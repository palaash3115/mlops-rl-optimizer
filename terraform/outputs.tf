output "api_ip" {
  description = "API container public IP"
  value       = azurerm_container_group.api.ip_address
}

output "streamlit_url" {
  description = "Streamlit public URL"
  value       = "http://${azurerm_container_group.streamlit.fqdn}:8501"
}

output "resource_group" {
  description = "Resource group name"
  value       = azurerm_resource_group.rl_optimizer.name
}
