terraform {
  required_version = ">= 1.5"

  required_providers {
    vercel = {
      source  = "vercel/vercel"
      version = "~> 2.0"
    }
    render = {
      source  = "render-oss/render"
      version = "~> 1.0"
    }
  }
}

provider "vercel" {
  api_token = var.vercel_api_token
}

provider "render" {
  api_key  = var.render_api_key
  owner_id = var.render_owner_id
}
