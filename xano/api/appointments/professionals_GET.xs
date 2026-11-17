// Returns active professionals to administrators and only the authenticated user to professionals.
query "appointments/professionals" verb=GET {
  api_group = "Appointments"
  auth = "user"

  input {
  }

  stack {
    db.get user {
      field_name = "id"
      field_value = $auth.id
      output = ["id", "name", "role", "status", "must_change_password", "barbershop_id"]
    } as $actor

    precondition ($actor != null && ($actor.status == "active" || $actor.status == "enabled")) {
      error_type = "accessdenied"
      error = "Conta profissional ativa obrigatória."
    }

    precondition ($actor.must_change_password != true) {
      error_type = "accessdenied"
      error = "É necessário trocar a senha antes de acessar a agenda."
    }

    function.run "Quick Start/authorize_professional_scope" {
      input = {
        actor_id: $auth.id
        target_professional_id: 0
      }
    } as $scope_check

    conditional {
      if ($actor.role == "admin") {
        db.query user {
          where = (
              ($db.user.role == "professional" || $db.user.role == "admin")
                && ($db.user.status == "active" || $db.user.status == "enabled")
                && (
                  $db.user.barbershop_id == $scope_check.barbershop_id
                  || ($scope_check.include_legacy_rows == true && $db.user.barbershop_id == null)
                )
          )
          sort = {user.name: "asc"}
          output = ["id", "name"]
          return = {type: "list"}
        } as $professionals
      }
      else {
        var $professionals {
          value = [{id: $actor.id, name: $actor.name}]
        }
      }
    }
  }

  response = $professionals
  guid = "PUU2IvB8AxeSTOdapUAvHkAztFk"
}
