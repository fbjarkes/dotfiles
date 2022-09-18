aws-login () {
  # do the AWS login flow if we don't have a valid login
  aws sts get-caller-identity > /dev/null || aws sso login

  JSON_FILE=$(ls $HOME/.aws/cli/cache/*.json)
  export AWS_ACCESS_KEY_ID=$(jq -r '.Credentials.AccessKeyId' $JSON_FILE)
  export AWS_SECRET_ACCESS_KEY=$(jq -r '.Credentials.SecretAccessKey' $JSON_FILE)
  export AWS_SESSION_TOKEN=$(jq -r '.Credentials.SessionToken' $JSON_FILE)
}

