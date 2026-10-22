// Administrators can query both active and inactive services.
query "services/admin" verb=GET {
  api_group = "Services"
  auth = "user"

  input {
  }

  stack {
    db.get user {
      field_name = "id"
      field_value = $auth.id
      output = ["id", "role", "status", "must_change_password"]
    } as $user

    precondition ($user != null) {
      error_type = "accessdenied"
      error = "Invalid authenticated user."
    }

    precondition ($user.status == "active") {
      error_type = "accessdenied"
      error = "User account is inactive."
    }

    precondition ($user.must_change_password != true) {
      error_type = "accessdenied"
      error = "Password change is required before using protected operations."
    }

    precondition ($user.role == "admin") {
      error_type = "accessdenied"
      error = "User does not have the required role to perform this action. Required: admin."
    }

    db.query service {
      return = {type: "list"}
    } as $services
  }

  response = $services
  guid = "dXgzGxC3uyzw6hL3ufhwO0yu2Xo"
}
