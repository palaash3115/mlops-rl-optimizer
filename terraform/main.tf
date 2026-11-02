terraform {
  required_version = ">= 1.8"

  required_providers {
    kind = {
      source  = "tehcyx/kind"
      version = "~> 0.4"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.31"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
  }
}

# ── Variables ────────────────────────────────────────────────────────────────
variable "cluster_name" {
  description = "Name of the local kind cluster"
  default     = "rl-optimizer-cluster"
}

variable "image_tag" {
  description = "Docker image tag to deploy"
  default     = "latest"
}

variable "image_name" {
  description = "Docker image name (local or GHCR)"
  default     = "rl-prompt-optimizer"
}

# ── Local kind cluster ───────────────────────────────────────────────────────
resource "kind_cluster" "this" {
  name = var.cluster_name

  kind_config {
    kind        = "Cluster"
    api_version = "kind.x-k8s.io/v1alpha4"

    node {
      role = "control-plane"
      extra_port_mappings {
        container_port = 30080
        host_port      = 8080
        listen_address = "0.0.0.0"
        protocol       = "TCP"
      }
    }
  }
}

# ── Load the local Docker image into kind ───────────────────────────────────
resource "null_resource" "load_image" {
  depends_on = [kind_cluster.this]

  triggers = {
    image = "${var.image_name}:${var.image_tag}"
  }

  provisioner "local-exec" {
    command = "kind load docker-image ${var.image_name}:${var.image_tag} --name ${var.cluster_name}"
  }
}

# ── Kubernetes provider pointing at the kind cluster ─────────────────────────
provider "kubernetes" {
  host                   = kind_cluster.this.endpoint
  cluster_ca_certificate = base64decode(kind_cluster.this.cluster_ca_certificate)
  client_certificate     = base64decode(kind_cluster.this.client_certificate)
  client_key             = base64decode(kind_cluster.this.client_key)
}

# ── Deploy k8s manifests ─────────────────────────────────────────────────────
resource "kubernetes_manifest" "configmap" {
  depends_on = [kind_cluster.this]
  manifest   = yamldecode(file("${path.module}/../k8s/configmap.yaml"))
}

resource "kubernetes_manifest" "deployment" {
  depends_on = [null_resource.load_image, kubernetes_manifest.configmap]
  manifest   = yamldecode(file("${path.module}/../k8s/deployment.yaml"))
}

resource "kubernetes_manifest" "service" {
  depends_on = [kubernetes_manifest.deployment]
  manifest   = yamldecode(file("${path.module}/../k8s/service.yaml"))
}

resource "kubernetes_manifest" "hpa" {
  depends_on = [kubernetes_manifest.deployment]
  manifest   = yamldecode(file("${path.module}/../k8s/hpa.yaml"))
}

# ── Outputs ──────────────────────────────────────────────────────────────────
output "cluster_name" {
  value = kind_cluster.this.name
}

output "kubeconfig_path" {
  value = kind_cluster.this.kubeconfig_path
}

output "api_url" {
  description = "Local API URL (via NodePort → port-forward)"
  value       = "http://localhost:8080"
}
