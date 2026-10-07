// Allows administrators to access any professional's data and professionals only their own.
function "Quick Start/authorize_professional_scope" {
  input {
    int actor_id
    int target_professional_id
  }

  stack {
    db.get user {
      field_name = "id"
      field_value = $input.actor_id
      output = ["id", "role", "status", "must_change_password"]
    } as $actor

    precondition ($actor != null && $actor.status == "active") {
      error_type = "accessdenied"
      error = "Active professional account required."
    }

    precondition ($actor.must_change_password == false) {
      error_type = "accessdenied"
      error = "Password change is required before accessing appointments."
    }

    conditional {
      if ($actor.role != "admin" && $actor.id != $input.target_professional_id) {
        throw {
          name = "accessdenied"
          value = "Professionals may only access their own appointments."
        }
      }
    }
  }

  response = true
}