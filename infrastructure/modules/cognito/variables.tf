variable "name_prefix" {
  type        = string
  description = "Prefix for Cognito resource names."
}

variable "domain_prefix" {
  type        = string
  description = "Unique Cognito hosted UI domain prefix."

  validation {
    condition     = trimspace(var.domain_prefix) != ""
    error_message = "domain_prefix must be non-empty."
  }
}

variable "callback_urls" {
  type        = list(string)
  description = "Allowed OAuth callback URLs for the public app client."

  validation {
    condition     = length(var.callback_urls) > 0
    error_message = "callback_urls must include at least one URL."
  }
}

variable "logout_urls" {
  type        = list(string)
  description = "Allowed OAuth logout URLs for the public app client."

  validation {
    condition     = length(var.logout_urls) > 0
    error_message = "logout_urls must include at least one URL."
  }
}

variable "tags" {
  type        = map(string)
  description = "Additional tags for module-created resources."
  default     = {}
}
