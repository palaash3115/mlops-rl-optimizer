terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
  required_version = ">= 1.3.0"
}

provider "azurerm" {
  features {}
}

# ── Resource Group ─────────────────────────────────────────────────────────
resource "azurerm_resource_group" "rl_optimizer" {
  name     = var.resource_group_name
  location = var.location
  tags     = var.tags
}

# ── Azure Container Instance — API ─────────────────────────────────────────
resource "azurerm_container_group" "api" {
  name                = "${var.app_name}-api"
  location            = azurerm_resource_group.rl_optimizer.location
  resource_group_name = azurerm_resource_group.rl_optimizer.name
  os_type             = "Linux"
  restart_policy      = "Always"

  container {
    name   = "api"
    image  = var.docker_image
    cpu    = "1.0"
    memory = "2.0"

    ports {
      port     = 8000
      protocol = "TCP"
    }

    environment_variables = {
      RLPROMPT_DB = "/app/data/rlprompt_app.db"
    }

    secure_environment_variables = {
      GEMINI_API_KEY = var.gemini_api_key
      GROQ_API_KEY   = var.groq_api_key
    }

    volume {
      name       = "data"
      mount_path = "/app/data"
      empty_dir  = true
    }

    liveness_probe {
      http_get {
        path   = "/health"
        port   = 8000
        scheme = "Http"
      }
      initial_delay_seconds = 10
      period_seconds        = 30
    }
  }

  tags = var.tags
}

# ── Azure Container Instance — Streamlit ───────────────────────────────────
resource "azurerm_container_group" "streamlit" {
  name                = "${var.app_name}-streamlit"
  location            = azurerm_resource_group.rl_optimizer.location
  resource_group_name = azurerm_resource_group.rl_optimizer.name
  os_type             = "Linux"
  ip_address_type     = "Public"
  dns_name_label      = "${var.app_name}-ui"
  restart_policy      = "Always"

  container {
    name   = "streamlit"
    image  = var.docker_image
    cpu    = "0.5"
    memory = "1.0"

    ports {
      port     = 8501
      protocol = "TCP"
    }

    environment_variables = {
      API_URL = "http://${azurerm_container_group.api.ip_address}:8000"
    }

    commands = ["streamlit", "run", "streamlit_app.py",
                "--server.port=8501", "--server.address=0.0.0.0"]
  }

  tags = var.tags
}
