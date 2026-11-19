// Creates a barbershop and its first administrator after the legacy migration.
query "auth/signup" verb=POST {
  api_group = "Authentication"

  input {
    text barbershop_name filters=trim
    text owner_name filters=trim
    email owner_email filters=trim|lower
    text owner_phone filters=trim
    text owner_password {
      sensitive = true
    }
  }

  stack {
    db.query barbershop {
      where = (
        $db.barbershop.migration_key == "legacy-default"
        && $db.barbershop.legacy_compatibility == true
        && $db.barbershop.status == "active"
      )
      return = {type: "single"}
    } as $migration

    precondition ($migration != null) {
      error_type = "accessdenied"
      error = "O cadastro de novas barbearias ainda não está disponível."
    }

    precondition (
      $input.barbershop_name != ""
      && ($input.barbershop_name|strlen) <= 120
    ) {
      error_type = "inputerror"
      error = "Informe um nome de barbearia com até 120 caracteres."
    }

    precondition (
      $input.owner_name != ""
      && ($input.owner_name|strlen) <= 120
      && $input.owner_email != ""
    ) {
      error_type = "inputerror"
      error = "Informe nome e e-mail válidos para a pessoa proprietária."
    }

    precondition (($input.owner_password|strlen) >= 8) {
      error_type = "inputerror"
      error = "A senha deve ter pelo menos 8 caracteres, uma letra e um número."
    }

    var $password_without_letters {
      value = $input.owner_password|regex_replace:"[A-Za-z]":""
    }

    var $password_without_digits {
      value = $input.owner_password|regex_replace:"[0-9]":""
    }

    precondition (
      ($password_without_letters|strlen) < ($input.owner_password|strlen)
      && ($password_without_digits|strlen) < ($input.owner_password|strlen)
    ) {
      error_type = "inputerror"
      error = "A senha deve ter pelo menos 8 caracteres, uma letra e um número."
    }

    var $normalized_phone {
      value = "/[^0-9]/"|regex_replace:"":$input.owner_phone
    }

    conditional {
      if (($normalized_phone|starts_with:"55") && (($normalized_phone|strlen) == 12 || ($normalized_phone|strlen) == 13)) {
        var.update $normalized_phone {
          value = "/^55/"|regex_replace:"":$normalized_phone
        }
      }
    }

    precondition (($normalized_phone|strlen) == 10 || ($normalized_phone|strlen) == 11) {
      error_type = "inputerror"
      error = "Informe um telefone com DDD e 10 ou 11 dígitos."
    }

    precondition (
      ($normalized_phone|starts_with:"00") == false
      && ($normalized_phone|starts_with:"01") == false
      && ($normalized_phone|starts_with:"10") == false
    ) {
      error_type = "inputerror"
      error = "Informe um DDD válido."
    }

    db.query user {
      where = $db.user.email == $input.owner_email
      return = {type: "single"}
    } as $existing_user

    precondition ($existing_user == null) {
      error_type = "inputerror"
      error = "Este e-mail já está associado a uma conta."
    }

    db.query user {
      where = $db.user.phone == $normalized_phone
      return = {type: "single"}
    } as $existing_phone_user

    precondition ($existing_phone_user == null) {
      error_type = "inputerror"
      error = "Este telefone já está associado a uma conta em outra barbearia."
    }

    security.create_uuid as $barbershop_migration_key

    db.transaction {
      stack {
        db.add barbershop {
          data = {
            created_at: "now"
            name: $input.barbershop_name
            status: "active"
            migration_key: $barbershop_migration_key
            weekly_hours: [
              {day_of_week: 1, intervals: []}
              {day_of_week: 2, intervals: []}
              {day_of_week: 3, intervals: []}
              {day_of_week: 4, intervals: []}
              {day_of_week: 5, intervals: []}
              {day_of_week: 6, intervals: []}
              {day_of_week: 7, intervals: []}
            ]
          }
        } as $barbershop

        db.add user {
          data = {
            created_at: "now"
            barbershop_id: $barbershop.id
            name: $input.owner_name
            email: $input.owner_email
            phone: $normalized_phone
            password: $input.owner_password
            role: "admin"
            status: "active"
            must_change_password: false
          }
        } as $owner

        db.add event_log {
          data = {
            created_at: "now"
            user_id: $owner.id
            barbershop_id: $barbershop.id
            action: "barbershop_registered"
            metadata: {barbershop_id: $barbershop.id}
          }
        } as $event_log
      }
    }
  }

  response = {
    success: true
    barbershop: {
      id: $barbershop.id
      name: $barbershop.name
    }
    owner: {
      id: $owner.id
      name: $owner.name
      email: $owner.email
      role: $owner.role
    }
  }
  tags = ["xano:quick-start"]
  guid = "YY0A9CZxcz-rnp_XKQbX5I7Sm_A"
}
