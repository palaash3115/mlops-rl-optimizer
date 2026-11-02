variable "resource_group_name" {
  description = "Azure Resource Group name"
  type        = string
  default     = "rg-rl-optimizer"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "East US"
}

variable "app_name" {
  description = "Application name prefix"
  type        = string
  default     = "rl-optimizer"
}

variable "docker_image" {
  description = "Docker image to deploy (from GHCR or ACR)"
  type        = string
  default     = "ghcr.io/your-github-username/mlopsproject-api:latest"
}

variable "gemini_api_key" {
  description = "Gemini API key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "groq_api_key" {
  description = "Groq API key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default = {
    project     = "rl-prompt-optimizer"
    environment = "production"
    managed_by  = "terraform"
  }
}
