query "services" verb=POST {
  api_group = "Services"
  auth = "user"

  input {
    text name filters=trim
    text description? filters=trim
    decimal price
    int duration_minutes
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "admin"}
    } as $role_check

    precondition ($input.name != "") {
      error_type = "inputerror"
      error = "Informe o nome do serviço."
    }

    precondition ($input.price >= 0 && $input.price == ($input.price|round:2)) {
      error_type = "inputerror"
      error = "O preço deve ser não negativo e ter no máximo duas casas decimais."
    }

    precondition ($input.duration_minutes > 0) {
      error_type = "inputerror"
      error = "A duração deve ser um número positivo de minutos."
    }

    db.add service {
      data = {
        created_at      : "now"
        updated_at      : "now"
        name            : $input.name
        description     : $input.description
        price           : $input.price
        duration_minutes: $input.duration_minutes
        status          : "active"
      }
    } as $service
  }

  response = $service
  guid = "1OXiMhAaT3FOI7Njr1aQTzj8xo4"
}
