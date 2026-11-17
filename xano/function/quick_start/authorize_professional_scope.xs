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
      output = ["id", "role", "status", "must_change_password", "barbershop_id"]
    } as $actor

    precondition ($actor != null && ($actor.status == "active" || $actor.status == "enabled")) {
      error_type = "accessdenied"
      error = "Active professional account required."
    }

    precondition ($actor.must_change_password == false) {
      error_type = "accessdenied"
      error = "Password change is required before accessing appointments."
    }

    function.run "Quick Start/enforce_role" {
      input = {
        user_id: $input.actor_id
        required_role: "professional"
      }
    } as $access_scope

    var $target_barbershop_id {
      value = null
    }

    conditional {
      if ($actor.role != "admin" && $actor.id != $input.target_professional_id) {
        throw {
          name = "accessdenied"
          value = "Professionals may only access their own appointments."
        }
      }
    }

    conditional {
      if ($input.target_professional_id > 0) {
        db.get user {
          field_name = "id"
          field_value = $input.target_professional_id
          output = ["id", "barbershop_id"]
        } as $target_professional

        precondition (
          $target_professional != null
          && (
            $target_professional.barbershop_id == $access_scope.barbershop_id
            || (
              $access_scope.include_legacy_rows == true
              && $target_professional.barbershop_id == null
            )
          )
        ) {
          error_type = "accessdenied"
          error = "Professional does not belong to this barbershop."
        }
      }
    }
  }

  response = {
    barbershop_id: $access_scope.barbershop_id
    include_legacy_rows: $access_scope.include_legacy_rows
  }
  guid = "oJm-O2VoyNCN-6h1vhvfcNaK_9g"
}