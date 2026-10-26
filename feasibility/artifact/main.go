// Linux-only feasibility provider. No content write or create operation exists.
package main

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/hashicorp/terraform-plugin-sdk/v2/diag"
	"github.com/hashicorp/terraform-plugin-sdk/v2/helper/schema"
	"github.com/hashicorp/terraform-plugin-sdk/v2/plugin"
	"golang.org/x/sys/unix"
)

type sandbox struct {
	root     string
	identity string
}
type receipt struct {
	Path         string `json:"path"`
	SHA256       string `json:"sha256"`
	Owner        string `json:"owner"`
	ResourceID   string `json:"resource_id"`
	Physical     string `json:"physical"`
	RootIdentity string `json:"root_identity"`
}

func identity(s *unix.Stat_t) string { return fmt.Sprintf("%d:%d", s.Dev, s.Ino) }

// Open every directory component with O_NOFOLLOW, including absolute root parents.
// Holding directory descriptors prevents a renamed parent from redirecting access.
func openDir(path string) (int, error) {
	if !filepath.IsAbs(path) || filepath.Clean(path) != path {
		return -1, fmt.Errorf("root must be canonical absolute path")
	}
	fd, err := unix.Open("/", unix.O_DIRECTORY|unix.O_RDONLY|unix.O_CLOEXEC, 0)
	if err != nil {
		return -1, err
	}
	for _, part := range strings.Split(strings.TrimPrefix(path, "/"), "/") {
		if part == "" {
			continue
		}
		next, e := unix.Openat(fd, part, unix.O_DIRECTORY|unix.O_RDONLY|unix.O_NOFOLLOW|unix.O_CLOEXEC, 0)
		unix.Close(fd)
		if e != nil {
			return -1, e
		}
		fd = next
	}
	return fd, nil
}
func parent(s *sandbox, path string) (int, string, error) {
	if path == "" || path == "." || filepath.IsAbs(path) || filepath.Clean(path) != path || strings.HasPrefix(path, "../") {
		return -1, "", fmt.Errorf("invalid relative locator")
	}
	fd, err := openDir(s.root)
	if err != nil {
		return -1, "", err
	}
	var st unix.Stat_t
	if err = unix.Fstat(fd, &st); err != nil || identity(&st) != s.identity {
		unix.Close(fd)
		return -1, "", fmt.Errorf("sandbox root identity changed")
	}
	parts := strings.Split(path, "/")
	for _, part := range parts[:len(parts)-1] {
		next, e := unix.Openat(fd, part, unix.O_DIRECTORY|unix.O_RDONLY|unix.O_NOFOLLOW|unix.O_CLOEXEC, 0)
		unix.Close(fd)
		if e != nil {
			return -1, "", e
		}
		fd = next
	}
	return fd, parts[len(parts)-1], nil
}
func inspect(fd int, name string) (string, string, error) {
	f, err := unix.Openat(fd, name, unix.O_RDONLY|unix.O_NOFOLLOW|unix.O_NONBLOCK|unix.O_CLOEXEC, 0)
	if err != nil {
		return "", "", err
	}
	file := os.NewFile(uintptr(f), name)
	defer file.Close()
	var st unix.Stat_t
	if err = unix.Fstat(f, &st); err != nil {
		return "", "", err
	}
	if st.Mode&unix.S_IFMT != unix.S_IFREG || st.Nlink != 1 {
		return "", "", fmt.Errorf("requires regular file with one link")
	}
	h := sha256.New()
	if _, err = io.Copy(h, file); err != nil {
		return "", "", err
	}
	return identity(&st), hex.EncodeToString(h.Sum(nil)), nil
}
func fromState(d *schema.ResourceData) receipt {
	return receipt{d.Get("path").(string), d.Get("sha256").(string), d.Get("owner").(string), d.Get("resource_id").(string), d.Get("physical").(string), d.Get("root_identity").(string)}
}
func check(s *sandbox, r receipt) (int, string, error) {
	if r.RootIdentity != s.identity {
		return -1, "", fmt.Errorf("receipt root mismatch")
	}
	fd, name, err := parent(s, r.Path)
	if err != nil {
		return -1, "", err
	}
	physical, digest, err := inspect(fd, name)
	if err == nil && (physical != r.Physical || digest != r.SHA256) {
		err = fmt.Errorf("immutable artifact identity/content mismatch; refusing operation")
	}
	if err != nil {
		unix.Close(fd)
		return -1, "", err
	}
	return fd, name, nil
}
func read(_ context.Context, d *schema.ResourceData, meta interface{}) diag.Diagnostics {
	fd, _, err := check(meta.(*sandbox), fromState(d))
	if err == unix.ENOENT {
		d.SetId("")
		return nil
	}
	if err != nil {
		return diag.FromErr(err)
	}
	unix.Close(fd)
	return nil
}
func remove(_ context.Context, d *schema.ResourceData, meta interface{}) diag.Diagnostics {
	fd, name, err := check(meta.(*sandbox), fromState(d))
	if err == unix.ENOENT {
		d.SetId("")
		return nil
	}
	if err != nil {
		return diag.FromErr(err)
	}
	defer unix.Close(fd)
	// Recheck immediately before unlink. Still not atomic against an external writer.
	p, h, err := inspect(fd, name)
	r := fromState(d)
	if err != nil || p != r.Physical || h != r.SHA256 {
		return diag.Errorf("pre-unlink mismatch; outcome unknown")
	}
	if err = unix.Unlinkat(fd, name, 0); err != nil && err != unix.ENOENT {
		return diag.FromErr(err)
	}
	if os.Getenv("DML_ARTIFACT_TEST_PAUSE_AFTER_UNLINK") == "1" {
		// Bounded fault-injection window for killing the actual CLI/plugin process.
		time.Sleep(10 * time.Second)
	}
	d.SetId("")
	return nil
}
func adopt(_ context.Context, d *schema.ResourceData, meta interface{}) ([]*schema.ResourceData, error) {
	var r receipt
	dec := json.NewDecoder(strings.NewReader(d.Id()))
	dec.DisallowUnknownFields()
	if err := dec.Decode(&r); err != nil {
		return nil, err
	}
	if r.Owner == "" || r.ResourceID == "" || len(r.SHA256) != 64 || r.Physical == "" || r.RootIdentity == "" {
		return nil, fmt.Errorf("incomplete adoption receipt")
	}
	fd, _, err := check(meta.(*sandbox), r)
	if err != nil {
		return nil, err
	}
	unix.Close(fd)
	fields := map[string]string{"path": r.Path, "sha256": r.SHA256, "owner": r.Owner, "resource_id": r.ResourceID, "physical": r.Physical, "root_identity": r.RootIdentity}
	for key, value := range fields {
		if err := d.Set(key, value); err != nil {
			return nil, err
		}
	}
	d.SetId(r.ResourceID)
	return []*schema.ResourceData{d}, nil
}
func provider() *schema.Provider {
	immutable := func() *schema.Schema { return &schema.Schema{Type: schema.TypeString, Required: true} }
	r := &schema.Resource{
		Schema: map[string]*schema.Schema{
			"path": immutable(), "sha256": immutable(), "owner": immutable(), "resource_id": immutable(),
			"physical": {Type: schema.TypeString, Computed: true}, "root_identity": {Type: schema.TypeString, Computed: true},
			"metadata": {Type: schema.TypeString, Optional: true, Default: ""},
		},
		CreateContext: func(context.Context, *schema.ResourceData, interface{}) diag.Diagnostics {
			return diag.Errorf("adoption-only: creation/replacement forbidden; import an existing artifact with a receipt")
		},
		ReadContext: read,
		UpdateContext: func(ctx context.Context, d *schema.ResourceData, m interface{}) diag.Diagnostics {
			for _, key := range []string{"path", "sha256", "owner", "resource_id"} {
				if d.HasChange(key) {
					return diag.Errorf("immutable field %s changed", key)
				}
			}
			return read(ctx, d, m)
		},
		DeleteContext: remove,
		CustomizeDiff: func(_ context.Context, d *schema.ResourceDiff, _ interface{}) error {
			if d.Id() != "" {
				for _, key := range []string{"path", "sha256", "owner", "resource_id"} {
					if d.HasChange(key) {
						return fmt.Errorf("immutable field %s changed; explicit retirement and separately authorized import required", key)
					}
				}
			}
			return nil
		},
		Importer: &schema.ResourceImporter{StateContext: adopt},
	}
	return &schema.Provider{
		Schema:       map[string]*schema.Schema{"root": {Type: schema.TypeString, Required: true}},
		ResourcesMap: map[string]*schema.Resource{"immutable_artifact": r},
		ConfigureContextFunc: func(_ context.Context, d *schema.ResourceData) (interface{}, diag.Diagnostics) {
			root := d.Get("root").(string)
			if root == "/" {
				return nil, diag.Errorf("root / forbidden")
			}
			fd, err := openDir(root)
			if err != nil {
				return nil, diag.FromErr(err)
			}
			defer unix.Close(fd)
			var st unix.Stat_t
			if err = unix.Fstat(fd, &st); err != nil {
				return nil, diag.FromErr(err)
			}
			return &sandbox{root, identity(&st)}, nil
		},
	}
}
func main() { plugin.Serve(&plugin.ServeOpts{ProviderFunc: provider}) }
