// Checks that a user has the appropriate role level. This example sets a hierarchy of roles, and a user must pass the minimum level to execute.
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
      value = {admin: 2, member: 1}
    }
  
    // Retrieve the user's role from the database.
    db.get user {
      field_name = "id"
      field_value = $input.user_id
      output = ["role"]
    } as $user
  
    // Ensure the user exists
    precondition ($user != null) {
      error_type = "inputerror"
      error = "User not found with the provided ID."
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
    precondition ($required_role_level > 0) {
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