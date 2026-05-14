# =============================================================================
# Vercel Project (Next.js Frontend)
# =============================================================================

resource "vercel_project" "frontend" {
  name      = "giinscore"
  framework = "nextjs"

  git_repository = {
    type = "github"
    repo = "${var.github_org}/${var.github_repo}"
  }

  root_directory = "frontend"

  build_command   = "npm run build"
  output_directory = ".next"
}

# =============================================================================
# 環境変数
# =============================================================================

resource "vercel_project_environment_variable" "api_url" {
  project_id = vercel_project.frontend.id
  key        = "NEXT_PUBLIC_API_URL"
  value      = "${local.backend_url}/api/v1"
  target     = ["production", "preview"]
}

# =============================================================================
# カスタムドメイン（設定されている場合のみ）
# =============================================================================

resource "vercel_project_domain" "custom" {
  count      = var.frontend_domain != "" ? 1 : 0
  project_id = vercel_project.frontend.id
  domain     = var.frontend_domain
}
