# Informative lab module, copied into each fresh ignored sandbox by probe.py.
terraform {
  required_providers {
    local = {
      source = "hashicorp/local"
      version = "= 2.5.3"
      configuration_aliases = [local.bound]
    }
  }
}
variable "directory" { type = string }
variable "label" { type = string }
variable "shared_id" { type = string }
resource "terraform_data" "binding" {
  input = { label = var.label, shared_id = var.shared_id }
}
resource "local_file" "artifact" {
  provider = local.bound
  filename = "${var.directory}/${var.label}.txt"
  content = terraform_data.binding.output.label
  file_permission = "0600"
  directory_permission = "0700"
}
output "binding" {
  value = {
    occurrence_id = terraform_data.binding.id
    filename = local_file.artifact.filename
    sha256 = local_file.artifact.content_sha256
    shared_id = terraform_data.binding.output.shared_id
  }
}
