// Allows an authenticated professional to change only their own password.
query "auth/change-password" verb=POST {
  api_group = "Authentication"
  auth = "user"

  input {
    text current_password
    password new_password filters=min:8|minAlpha:1|minDigit:1
    text confirm_password
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "professional"}
    } as $role_check

    db.get user {
      field_name = "id"
      field_value = $auth.id
      output = ["id", "password", "role"]
    } as $user

    var $legacy_password_match {
      value = (($user.password != null) && ($user.password == $input.current_password))
    }

    conditional {
      if ($legacy_password_match == true) {
        var $password_matches {
          value = true
        }
      }
      else {
        security.check_password {
          text_password = $input.current_password
          hash_password = $user.password
        } as $password_matches
      }
    }

    precondition ($password_matches == true) {
      error_type = "accessdenied"
      error = "A senha atual está incorreta."
    }

    precondition ($input.new_password == $input.confirm_password) {
      error_type = "inputerror"
      error = "A confirmação da nova senha não confere."
    }

    precondition ($input.new_password != $input.current_password) {
      error_type = "inputerror"
      error = "A nova senha deve ser diferente da senha atual."
    }

    db.edit user {
      field_name = "id"
      field_value = $auth.id
      data = {
        password: $input.new_password
        must_change_password: false
      }
    } as $updated_user

    function.run "Quick Start/log_event" {
      input = {
        user_id: $auth.id
        action: "profile_password_changed"
        metadata: {role: $user.role}
      }
    } as $event_log
  }

  response = {success: true}
  guid = "GyMgSDzold_IdM_xvZb521cb-8Q"
}
