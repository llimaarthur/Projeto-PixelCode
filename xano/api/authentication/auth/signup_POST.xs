// Public signup is disabled; internal accounts are provisioned by the administrator.
query "auth/signup" verb=POST {
  api_group = "Authentication"

  input {
  }

  stack {
    throw {
      name = "accessdenied"
      value = "Public registration is disabled. Contact the barbershop administrator."
    }
  }

  response = null
  tags = ["xano:quick-start"]
  guid = "YY0A9CZxcz-rnp_XKQbX5I7Sm_A"
}