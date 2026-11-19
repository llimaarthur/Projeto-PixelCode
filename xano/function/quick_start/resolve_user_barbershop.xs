// Resolves a user's tenant and grants legacy-null access only to the initial barbershop.
function "Quick Start/resolve_user_barbershop" {
  input {
    int user_id
    bool bootstrap_legacy?=false
  }

  stack {
    db.get user {
      field_name = "id"
      field_value = $input.user_id
      output = ["id", "role", "barbershop_id"]
    } as $user

    precondition ($user != null) {
      error_type = "accessdenied"
      error = "User not found."
    }

    var $barbershop_id {
      value = $user.barbershop_id
    }

    conditional {
      if ($user.barbershop_id == null) {
        db.query barbershop {
          where = $db.barbershop.migration_key == "legacy-default"
          return = {type: "single"}
        } as $legacy_barbershop

        conditional {
          if ($legacy_barbershop == null) {
            precondition ($input.bootstrap_legacy == true && $user.role == "admin") {
              error_type = "accessdenied"
              error = "User account is not associated with a barbershop."
            }

            db.add barbershop {
              data = {
                created_at: "now"
                name: "Barbearia inicial"
                status: "active"
                migration_key: "legacy-default"
                migration_completed: false
                legacy_compatibility: true
              }
            } as $created_legacy

            var.update $barbershop_id {
              value = $created_legacy.id
            }
          }
          else {
            precondition (
              $legacy_barbershop.status == "active"
              && $legacy_barbershop.legacy_compatibility == true
            ) {
              error_type = "accessdenied"
              error = "User account is not associated with a barbershop."
            }

            var.update $barbershop_id {
              value = $legacy_barbershop.id
            }
          }
        }
      }
    }

    db.get barbershop {
      field_name = "id"
      field_value = $barbershop_id
      output = ["id", "name", "status", "migration_key", "legacy_compatibility"]
    } as $barbershop

    precondition ($barbershop != null && $barbershop.status == "active") {
      error_type = "accessdenied"
      error = "Barbershop account is inactive."
    }

    var $include_legacy_rows {
      value = (
        $barbershop.migration_key == "legacy-default"
        && $barbershop.legacy_compatibility == true
      )
    }
  }

  response = {
    barbershop_id: $barbershop.id
    barbershop_name: $barbershop.name
    include_legacy_rows: $include_legacy_rows
  }
  guid = "hPPZRjrlXOFL4Y6O2kc65nc673U"
}
