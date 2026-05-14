# =============================================================================
# PostgreSQL Database (Free)
# =============================================================================

resource "render_postgres" "db" {
  name   = "giinscore-db"
  plan   = "free"
  region = var.render_region

  database_name = "giinscore"
  database_user = "giinscore"

  version = "16"
}

# =============================================================================
# Backend Web Service (Starter, Docker)
# =============================================================================

resource "render_web_service" "backend" {
  name   = "giinscore-api"
  plan   = "starter"
  region = var.render_region

  runtime_source = {
    docker = {
      repo_url        = "https://github.com/${var.github_org}/${var.github_repo}"
      branch          = "master"
      dockerfile_path = "./backend/Dockerfile"
      context         = "./backend"
      auto_deploy     = true
    }
  }

  pre_deploy_command = "alembic upgrade head"

  env_vars = {
    "DATABASE_URL" = {
      value = render_postgres.db.connection_info.internal_connection_string
    }
    "CORS_ORIGINS" = {
      value = local.cors_origins
    }
    "KOKKAI_API_RATE_LIMIT" = {
      value = "1.0"
    }
    "DISCORD_WEBHOOK_URL" = {
      value = var.discord_webhook_url
    }
    "ANTHROPIC_API_KEY" = {
      value = var.anthropic_api_key
    }
  }
}

# =============================================================================
# Locals
# =============================================================================

locals {
  backend_url = render_web_service.backend.url

  # CORS: カスタムドメインがあればそれを使う、なければ Vercel のデフォルトURLを使う
  cors_origins = var.cors_origins != "" ? var.cors_origins : (
    var.frontend_domain != "" ? "https://${var.frontend_domain}" : "https://giinscore.vercel.app"
  )
}
