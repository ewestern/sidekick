resource "aws_secretsmanager_secret" "openai_api_key" {
  name        = "/sidekick/production/openai_api_key"
  description = "OpenAI API key for Sidekick services"
}

data "aws_secretsmanager_secret_version" "openai_api_key" {
  secret_id = aws_secretsmanager_secret.openai_api_key.id
}

resource "aws_secretsmanager_secret" "hf_token" {
  name        = "/sidekick/production/hf_token"
  description = "Hugging Face token for WhisperX diarization (newsroom Batch transcription)"
}

data "aws_secretsmanager_secret_version" "hf_token" {
  secret_id = aws_secretsmanager_secret.hf_token.id
}