#!/usr/bin/env python3
"""Bounded trusted Floci Docker/S3 probe. Never pulls/builds; explicit profile acceptance required.
Run from repository root: python3 -B feasibility/floci/probe.py --accepted-private-profile
Retains all owned resources on unknown writer disposition. No cloud/SDK/dependencies.
"""
import argparse
import base64
import hashlib
import json
import re
import subprocess
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOCKER = ['docker', '--host', 'unix:///var/run/docker.sock']
FLOCI = 'docker.io/floci/floci@sha256:09b72c45f333019adecb302e79c6b746e290135f528016c8514618bc7ab02344'
NODE = 'sha256:00e9195ebd49985a6da8921f419978d85dfe354589755192dc090425ce4da2f7'
SHA = 'ee15f502bfc017861b67b076b82e1ccd032c7129'
CLIENT = r'''
const http=require('http');
const q=JSON.parse(process.argv[1]);
const req=http.request({hostname:'floci',port:4566,path:q.path,method:q.method,
 headers:{'Content-Type':q.json?'application/json':'application/octet-stream',
 'Authorization':'AWS4-HMAC-SHA256 Credential=test/20261029/us-east-1/'+q.service+'/aws4_request, SignedHeaders=host, Signature=00',
 'X-Amz-Date':'20261029T000000Z'}},res=>{
 let a=[],n=0;res.on('data',x=>{n+=x.length;if(n>1048576){req.destroy(Error('response bound'));return;}a.push(x)});
 res.on('end',()=>console.log(JSON.stringify({status:res.statusCode,body:Buffer.concat(a).toString('base64')})));
});
const timer=setTimeout(()=>req.destroy(Error('finite API deadline')),5000);
req.on('close',()=>clearTimeout(timer)); req.on('error',e=>{console.error(e.message);process.exitCode=1});
req.end(Buffer.from(q.body,'base64'));
'''
JOB = r'''
const http=require('http'),crypto=require('crypto');
const prefix='/dml-floci/'+process.env.PROBE_PREFIX;
function call(method,key,data){return new Promise((resolve,reject)=>{
 const req=http.request({hostname:'floci',port:4566,path:prefix+'/'+key,method,
 headers:{'Content-Type':'application/octet-stream','Authorization':'AWS4-HMAC-SHA256 Credential=test/20261029/us-east-1/s3/aws4_request, SignedHeaders=host, Signature=00','X-Amz-Date':'20261029T000000Z'}},res=>{
 let a=[],n=0;res.on('data',x=>{n+=x.length;if(n>1048576)req.destroy(Error('response bound'));else a.push(x)});
 res.on('end',()=>resolve({status:res.statusCode,body:Buffer.concat(a)}));});
 const timer=setTimeout(()=>req.destroy(Error('request deadline')),5000);req.on('close',()=>clearTimeout(timer));req.on('error',reject);req.end(data);
});}
async function put(key,value){let r=await call('PUT',key,Buffer.from(JSON.stringify(value)));if(r.status!==200)throw Error('put '+r.status);}
async function gate(key){const deadline=Date.now()+60000;while(Date.now()<deadline){let r=await call('GET',key);if(r.status===200)return;if(r.status!==404)throw Error('gate '+r.status);await new Promise(r=>setTimeout(r,200));}throw Error('cooperative gate deadline');}
(async()=>{
 const identity={job:process.env.AWS_BATCH_JOB_ID,attempt:Number(process.env.AWS_BATCH_JOB_ATTEMPT),pid:process.pid,nonce:crypto.randomUUID()};
 await put('started',identity); await gate('gate1');
 let r=await call('GET','input');if(r.status!==200)throw Error('input '+r.status);const input=JSON.parse(r.body);
 let b=await call('GET','binary');if(b.status!==200)throw Error('binary '+b.status);
 const computed={...identity,sum:input.a+input.b,digest:crypto.createHash('sha256').update(b.body).digest('hex'),length:b.body.length};
 await put('progress',computed); await gate('gate2');await put('result',computed);
 console.log(JSON.stringify(computed));process.exitCode=Number(process.env.PROBE_EXIT);
})().catch(e=>{console.error(e.message);process.exitCode=91;});
'''


def released_service_enable_keys(app):
    """Read exact indent-scoped shipped service enabled fields, including comments/other first fields."""
    section = app.split('\n  services:\n', 1)[1]
    current = None
    found = []
    for line in section.splitlines():
        key = re.fullmatch(r'    ([a-z0-9-]+):(?:\s*#.*)?', line)
        if key:
            current = key.group(1)
        elif re.match(r'      enabled:\s*(true|false)(?:\s*#.*)?$', line):
            assert current is not None and current not in found
            found.append(current)
        elif line and not line.startswith('    ') and not line.lstrip().startswith('#'):
            current = None
    assert {'batch', 's3', 'cloudwatchlogs', 'iam', 'ec2'} <= set(found)
    return found


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--accepted-private-profile', action='store_true')
    p.add_argument('--prior-packet-replay', type=Path, help='prepared owned replay sandbox; skips new computational jobs')
    args = p.parse_args()
    if not args.accepted_private_profile:
        p.error('requires coordinator-accepted private network/socket profile; does not authorize a pull')
    run_id = uuid.uuid4().hex
    name = 'dml-floci-' + run_id
    net = name + '-net'
    vol = name + '-data'
    out = ROOT / 'runtime' / ('run-' + run_id)
    out.mkdir(parents=True, exist_ok=False)
    labels = ['--label', 'dml.feasibility=floci', '--label', 'dml.owner=' + run_id]
    calls = []
    clients = []
    jobs = []
    prefixes = []
    client_ids = {}
    summary = {'owner': run_id, 'network': net, 'service': name, 'volume': vol,
               'jobs': jobs, 'clients': clients, 'client_ids': client_ids,
               'runtime_pass': False, 'retired': False}

    def docker(*argv, check=True, timeout=30):
        command = DOCKER + list(argv)
        try:
            r = subprocess.run(command, capture_output=True, timeout=timeout)
            calls.append({'command': command, 'exit': r.returncode,
                          'stdout': r.stdout.decode(errors='replace'),
                          'stderr': r.stderr.decode(errors='replace')})
        except BaseException:
            calls.append({'command': command, 'exit': None, 'disposition': 'unknown'})
            raise
        (out / 'commands.json').write_text(json.dumps(calls, indent=2))
        if check and r.returncode:
            raise RuntimeError('Docker operation failed: ' + str(command) + ': ' + r.stderr.decode(errors='replace'))
        return r

    def api(method, path, data=b'', service='s3', as_json=False):
        client_name = name + '-client-' + str(len(clients))
        clients.append(client_name)
        query = json.dumps({'method': method, 'path': path, 'body': base64.b64encode(data).decode(),
                            'service': service, 'json': as_json}, separators=(',', ':'))
        docker('create', '--pull=never', '--name', client_name, *labels, '--network', net,
               '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--memory', '128m',
               '--cpus', '0.5', '--pids-limit', '64', '--no-healthcheck', NODE, 'node', '-e', CLIENT, query)
        client_ids[client_name] = json.loads(docker('inspect', client_name).stdout)[0]['Id']
        r = docker('start', '-a', client_name, timeout=20)
        state = json.loads(docker('inspect', client_name).stdout)[0]
        assert not state['State']['Running'] and state['State']['ExitCode'] == 0
        response = json.loads(r.stdout)
        body = base64.b64decode(response['body'], validate=True)
        return response['status'], body

    def batch(action, body):
        status, raw = api('POST', '/v1/' + action.lower(), json.dumps(body).encode(), 'batch', True)
        if status != 200:
            raise RuntimeError('Batch ' + action + ': ' + str(status) + ' ' + raw.decode(errors='replace'))
        return json.loads(raw)

    def put(prefix, key, data):
        status, body = api('PUT', '/dml-floci/' + prefix + '/' + key, data)
        assert status == 200, (status, body)

    def get(prefix, key):
        return api('GET', '/dml-floci/' + prefix + '/' + key)

    def await_object(prefix, key):
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            status, raw = get(prefix, key)
            if status == 200:
                return json.loads(raw)
            assert status == 404, (status, raw)
            time.sleep(.3)
        raise RuntimeError('bounded object wait expired: ' + key)

    def owned_children():
        r = docker('ps', '-aq', '--filter', 'label=floci_namespace=' + run_id)
        ids = r.stdout.decode().split()
        return json.loads(docker('inspect', *ids).stdout) if ids else []

    try:
        image = json.loads(docker('image', 'inspect', FLOCI).stdout)[0]
        assert image['Config']['Labels']['org.opencontainers.image.revision'] == SHA
        assert image['Config']['Labels']['org.opencontainers.image.version'] == '2.3.0'
        docker('image', 'inspect', NODE)
        docker('network', 'create', '--internal', '--driver', 'bridge', *labels, net)
        network = json.loads(docker('network', 'inspect', net).stdout)[0]
        assert network['Internal'] and network['Labels']['dml.owner'] == run_id
        summary['network_inspect'] = network
        docker('volume', 'create', *labels, vol)
        volume = json.loads(docker('volume', 'inspect', vol).stdout)[0]
        assert volume['Labels']['dml.owner'] == run_id
        summary['volume_inspect'] = volume
        app = (ROOT / 'runtime/sources/release/src/main/resources/application.yml').read_text()
        service_keys = released_service_enable_keys(app)
        env = {('FLOCI_SERVICES_' + k.replace('-', '_').upper() + '_ENABLED'):
               ('true' if k in {'batch', 's3', 'cloudwatchlogs', 'iam'} else 'false')
               for k in service_keys}
        summary['released_service_enable_keys'] = service_keys
        env.update(FLOCI_SERVICES_BATCH_RUNNER_MODE='docker', FLOCI_SERVICES_BATCH_DOCKER_NETWORK=net,
                   FLOCI_DOCKER_RESOURCE_NAMESPACE=run_id, FLOCI_HOSTNAME='floci', FLOCI_STORAGE_MODE='persistent',
                   FLOCI_STORAGE_PERSISTENT_PATH='/app/data', FLOCI_DNS_CONTAINER_FALLBACK_ENABLED='false',
                   FLOCI_DNS_CONTAINER_FALLBACK_SERVERS='127.0.0.1', FLOCI_DNS_SPOOF_AWS_ENDPOINTS='false',
                   FLOCI_TLS_ENABLED='false', LOCALSTACK_PARITY='false', FLOCI_SERVICES_ECS_TASK_ROLE_CREDENTIALS_ENABLED='false',
                   FLOCI_SERVICES_EC2_ENABLED='false')
        env_args = [a for k, v in env.items() for a in ['-e', k + '=' + v]]
        gid = str(Path('/var/run/docker.sock').stat().st_gid)
        assert gid == '131', 'profile socket GID changed; do not silently adapt'
        daemon = docker('info', '--format', '{{.Name}} {{.DockerRootDir}}').stdout.decode().strip()
        assert daemon == 'michas-robots /work/docker'
        summary['daemon'] = daemon
        docker('create', '--pull=never', '--name', name, *labels, '--network', net, '--network-alias', 'floci',
               '--no-healthcheck', '--user', '1001:0', '--group-add', gid, '--cap-drop', 'ALL',
               '--security-opt', 'no-new-privileges', '--memory', '512m', '--cpus', '1', '--pids-limit', '256',
               '--log-driver', 'json-file', '--log-opt', 'max-size=1m', '--log-opt', 'max-file=2',
               '--mount', 'type=bind,src=/var/run/docker.sock,dst=/var/run/docker.sock',
               '--mount', 'type=volume,src=' + vol + ',dst=/app/data', *env_args, FLOCI,
               '/app/application', '-Dquarkus.http.host=0.0.0.0', '-Dfloci.security.allow-unsafe-network-exposure=true')
        docker('start', name)
        time.sleep(3)
        service = json.loads(docker('inspect', name).stdout)[0]
        assert service['State']['Running'] and not service['HostConfig']['PortBindings']
        assert service['Config']['Labels']['dml.owner'] == run_id
        assert service['Config']['User'] == '1001:0'
        assert service['HostConfig']['GroupAdd'] == ['131']
        assert service['HostConfig']['CapDrop'] == ['ALL']
        assert service['HostConfig']['SecurityOpt'] == ['no-new-privileges']
        assert not service['HostConfig']['Privileged']
        assert service['HostConfig']['NetworkMode'] == net
        assert service['HostConfig']['Memory'] == 512 * 1024 * 1024
        assert service['HostConfig']['NanoCpus'] == 1000000000
        assert service['HostConfig']['PidsLimit'] == 256
        assert len(service['Mounts']) == 2
        assert {(x['Type'], x['Destination']) for x in service['Mounts']} == {('bind', '/var/run/docker.sock'), ('volume', '/app/data')}
        for mount in service['Mounts']:
            assert (mount['Source'] == '/var/run/docker.sock') if mount['Type'] == 'bind' else (mount['Name'] == vol)
        effective_env = dict(x.split('=', 1) for x in service['Config']['Env'])
        assert all(effective_env[k] == v for k, v in env.items())
        summary['service_inspect'] = service
        boot_logs = docker('logs', name)
        boot_text = (boot_logs.stdout + boot_logs.stderr).decode(errors='replace')
        (out / 'pre-submit-service.log').write_text(boot_text)
        enabled = re.findall(r'Enabled services: \[([^\]]*)\]', boot_text)
        assert enabled and set(enabled[-1].split(', ')) == {'s3', 'iam', 'cloudwatchlogs', 'batch'}
        assert 'EC2 IMDS server listening' not in boot_text
        bindings = docker('exec', name, 'cat', '/proc/net/tcp', '/proc/net/tcp6', '/proc/net/udp', '/proc/net/udp6').stdout.decode()
        (out / 'pre-submit-namespace-bindings.txt').write_text(bindings)
        for line in bindings.splitlines():
            fields = line.split()
            if len(fields) > 3 and ':' in fields[1]:
                assert fields[1].split(':')[-1] != '23D1', '9169 IMDS binding present'
        summary['private_9169_binding_absent'] = True
        summary['pre_submit_enabled_services'] = enabled[-1]
        batch('CreateComputeEnvironment', {'computeEnvironmentName': 'local', 'type': 'UNMANAGED'})
        batch('CreateJobQueue', {'jobQueueName': 'local', 'priority': 1,
                                'computeEnvironmentOrder': [{'order': 1, 'computeEnvironment': 'local'}]})
        batch('RegisterJobDefinition', {'jobDefinitionName': 'finite', 'type': 'container',
              'containerProperties': {'image': NODE, 'command': ['node', '-e', JOB],
                                      'resourceRequirements': [{'type': 'MEMORY', 'value': '128'}]},
              'retryStrategy': {'attempts': 1}})
        status, _ = api('PUT', '/dml-floci')
        assert status == 200
        binary = bytes(range(256)) * 16
        for expected_exit in (() if args.prior_packet_replay else (0, 23)):
            prefix = 'job-' + str(expected_exit)
            prefixes.append(prefix)
            put(prefix, 'input', b'{"a":13,"b":29}')
            put(prefix, 'binary', binary)
            response = batch('SubmitJob', {'jobName': name + '-' + str(expected_exit), 'jobQueue': 'local',
                         'jobDefinition': 'finite:1', 'retryStrategy': {'attempts': 1},
                         'containerOverrides': {'environment': [{'name': 'PROBE_PREFIX', 'value': prefix},
                                                                {'name': 'PROBE_EXIT', 'value': str(expected_exit)}]}})
            row = {'id': response['jobId'], 'prefix': prefix, 'expected_exit': expected_exit}
            jobs.append(row)
            row['started'] = await_object(prefix, 'started')
            assert row['started']['job'] == row['id'] and row['started']['attempt'] == 1
            row['gated_status'] = batch('DescribeJobs', {'jobs': [row['id']]})
            assert row['gated_status']['jobs'][0]['status'] == 'RUNNING'
            assert get(prefix, 'progress')[0] == 404
            before = owned_children()
            assert len(before) == 1 and before[0]['State']['Running']
            assert not before[0]['Mounts'] and not before[0]['HostConfig']['Privileged']
            child = before[0]
            assert child['Config']['Labels']['io.floci.service'] == 'batch'
            assert child['Config']['Labels']['io.floci.resource-id'] == row['id']
            assert child['HostConfig']['NetworkMode'] == net
            assert not child['HostConfig']['PortBindings']
            assert child['Image'] == NODE
            row['container_id'] = child['Id']
            row['container_inspect'] = child
            for _ in range(2):
                assert batch('DescribeJobs', {'jobs': [row['id']]})['jobs'][0]['status'] == 'RUNNING'
            after = owned_children()
            assert [x['Id'] for x in before] == [x['Id'] for x in after]
            put(prefix, 'gate1', b'released')
            row['progress'] = await_object(prefix, 'progress')
            assert row['progress']['sum'] == 42 and row['progress']['digest'] == hashlib.sha256(binary).hexdigest()
            assert batch('DescribeJobs', {'jobs': [row['id']]})['jobs'][0]['status'] == 'RUNNING'
            put(prefix, 'gate2', b'released')
            row['result'] = await_object(prefix, 'result')
            deadline = time.monotonic() + 25
            while time.monotonic() < deadline:
                row['final'] = batch('DescribeJobs', {'jobs': [row['id']]})['jobs'][0]
                if row['final']['status'] in {'SUCCEEDED', 'FAILED'}:
                    break
                time.sleep(.3)
            assert row['final']['status'] == ('SUCCEEDED' if expected_exit == 0 else 'FAILED')
            assert row['final']['container']['exitCode'] == expected_exit
            assert len(row['final']['attempts']) == 1
            assert row['final']['attempts'][0]['container']['exitCode'] == expected_exit
            assert row['result'] == row['progress']
            assert not owned_children()
        if args.prior_packet_replay:
            replay = args.prior_packet_replay.resolve()
            assert replay.is_relative_to(ROOT / 'runtime')
            selection = json.loads((replay / 'selection.json').read_bytes())
            for row in selection['packets']:
                label = row['label']
                assert re.fullmatch(r'[012]-(initial|publication|completion)-0', label)
                destination = replay / 'fetched' / label
                destination.mkdir(parents=True, exist_ok=False)
                for filename in ('job.json', 'observation.json', 'snapshot.bundle'):
                    data = (replay / 'selected' / label / filename).read_bytes()
                    assert hashlib.sha256(data).hexdigest() == row['files'][filename]['sha256']
                    put('replay-' + label, filename, data)
                    status, fetched = get('replay-' + label, filename)
                    assert status == 200 and fetched == data
                    (destination / filename).write_bytes(fetched)
            summary['prior_packet_files_transported'] = len(selection['packets']) * 3
        # Safe storage restart ONLY after the computational writers were confirmed absent.
        docker('stop', '-t', '20', name)
        assert not json.loads(docker('inspect', name).stdout)[0]['State']['Running']
        docker('start', name)
        time.sleep(3)
        for row in jobs:
            assert batch('DescribeJobs', {'jobs': [row['id']]})['jobs'][0] == row['final']
            assert json.loads(get(row['prefix'], 'result')[1]) == row['result']
        summary['after_reap_clean_restart'] = True
        summary['runtime_pass'] = True
    except BaseException as error:
        summary['error'] = type(error).__name__ + ': ' + str(error)
        raise
    finally:
        try:
            # Release all finite gates even on assertion/transport errors; never signal a job.
            for prefix in prefixes:
                for gate in ('gate1', 'gate2'):
                    put(prefix, gate, b'finally release')
            deadline = time.monotonic() + 75
            while owned_children() and time.monotonic() < deadline:
                time.sleep(1)
            children = owned_children()
            summary['final_children'] = children
            assert not children, 'owned computational child disposition unproved; retain fixture'
            # Every acquired API client must also be reaped before retirement.
            for client in clients:
                state = json.loads(docker('inspect', client).stdout)[0]
                assert state['Id'] == client_ids[client]
                assert state['Config']['Labels']['dml.owner'] == run_id
                assert not state['State']['Running'], 'retain live/unknown API client'
            docker('stop', '-t', '20', name)
            state = json.loads(docker('inspect', name).stdout)[0]
            assert not state['State']['Running']
            assert state['Id'] == summary['service_inspect']['Id']
            assert state['Config']['Labels']['dml.owner'] == run_id
            docker('cp', name + ':/app/data', str(out / 'service-data'))
            logs = docker('logs', name)
            (out / 'service.log').write_bytes(logs.stdout + logs.stderr)
            for client in clients:
                docker('rm', client_ids[client])
            docker('rm', state['Id'])
            assert json.loads(docker('volume', 'inspect', vol).stdout)[0]['Labels']['dml.owner'] == run_id
            docker('volume', 'rm', vol)
            current_network = json.loads(docker('network', 'inspect', net).stdout)[0]
            assert current_network['Id'] == summary['network_inspect']['Id'] and not current_network['Containers']
            docker('network', 'rm', current_network['Id'])
            summary['retired'] = True
        except BaseException as error:
            summary['cleanup_blocker'] = type(error).__name__ + ': ' + str(error)
        (out / 'summary.json').write_text(json.dumps(summary, indent=2))
        (out / 'commands.json').write_text(json.dumps(calls, indent=2))
        print(json.dumps({'evidence': str(out), 'runtime_pass': summary['runtime_pass'],
                          'retired': summary['retired'], 'cleanup_blocker': summary.get('cleanup_blocker')}))
    if not summary['retired']:
        raise RuntimeError('fixture retained pending disposition review')


if __name__ == '__main__':
    main()
