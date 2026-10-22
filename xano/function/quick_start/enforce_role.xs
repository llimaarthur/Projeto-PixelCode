// Checks that an active professional has the required role level.
function "Quick Start/enforce_role" {
  input {
    // The ID of the user to check the role for.
    int user_id
  
    // The role required to perform the action.
    text required_role
  }

  stack {
    // Defines a hierarchy of roles with numerical levels.
    var $role_hierarchy {
      value = {admin: 2, professional: 1}
    }
  
    // The endpoint passes the authenticated user's ID to this function.
    db.get user {
      field_name = "id"
      field_value = $input.user_id
      output = ["id", "role", "status", "must_change_password"]
    } as $user

    precondition ($user != null) {
      error_type = "inputerror"
      error = "User not found with the provided ID."
    }

    precondition ($user.status == "active") {
      error_type = "accessdenied"
      error = "User account is inactive."
    }

    precondition ($user.must_change_password != true) {
      error_type = "accessdenied"
      error = "Password change is required before using protected operations."
    }

    // Extract the user's role from the retrieved user data.
    var $user_role {
      value = $user.role
    }
  
    // Get the numerical level of the user's role. Defaults to 0 if not defined.
    var $user_role_level {
      value = $role_hierarchy|get:$user_role
    }
  
    // Get the numerical level of the required role. Defaults to 0 if not defined.
    var $required_role_level {
      value = $role_hierarchy|get:$input.required_role
    }
  
    // Ensure the required role is a valid, defined role in the hierarchy.
    precondition ($required_role_level != null) {
      error_type = "inputerror"
      error = "Invalid required role specified: " ~ $input.required_role
    }
  
    // Check if the user's role level is sufficient for the required role.
    conditional {
      if ($user_role_level < $required_role_level) {
        throw {
          name = "accessdenied"
          value = "User does not have the required role to perform this action. Required: " ~ $input.required_role ~ ", Actual: " ~ $user_role
        }
      }
    }
  }

  response = null
  tags = ["xano:quick-start"]
  guid = "5TI61jNQBwQzHtbbaZVzv1dFMoQ"
}