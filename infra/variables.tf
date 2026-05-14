# =============================================================================
# 認証
# =============================================================================

variable "vercel_api_token" {
  description = "Vercel API token (https://vercel.com/account/tokens)"
  type        = string
  sensitive   = true
}

variable "render_api_key" {
  description = "Render API key (https://dashboard.render.com/u/settings#api-keys)"
  type        = string
  sensitive   = true
}

variable "render_owner_id" {
  description = "Render owner ID (usr-xxx or tea-xxx)"
  type        = string
}

# =============================================================================
# GitHub
# =============================================================================

variable "github_org" {
  description = "GitHub organization or user name"
  type        = string
}

variable "github_repo" {
  description = "GitHub repository name"
  type        = string
  default     = "giin-score"
}

# =============================================================================
# ドメイン
# =============================================================================

variable "frontend_domain" {
  description = "Frontend custom domain (e.g. giinscore.example.com)"
  type        = string
  default     = ""
}

# =============================================================================
# Backend 環境変数
# =============================================================================

variable "cors_origins" {
  description = "Allowed CORS origins (comma-separated)"
  type        = string
  default     = ""
}

variable "discord_webhook_url" {
  description = "Discord webhook URL for notifications"
  type        = string
  sensitive   = true
  default     = ""
}

variable "anthropic_api_key" {
  description = "Anthropic API key for LLM analysis"
  type        = string
  sensitive   = true
  default     = ""
}

# =============================================================================
# Render リージョン
# =============================================================================

variable "render_region" {
  description = "Render deployment region"
  type        = string
  default     = "oregon"
}
