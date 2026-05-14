output "frontend_url" {
  description = "Frontend URL (Vercel)"
  value       = var.frontend_domain != "" ? "https://${var.frontend_domain}" : "https://giinscore.vercel.app"
}

output "backend_url" {
  description = "Backend API URL (Render)"
  value       = local.backend_url
}

output "api_docs_url" {
  description = "Backend API docs (Swagger UI)"
  value       = "${local.backend_url}/docs"
}

output "database_name" {
  description = "PostgreSQL database name"
  value       = render_postgres.db.database_name
}
