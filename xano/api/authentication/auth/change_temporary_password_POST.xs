// Completes the required password change for a newly provisioned professional.
query "auth/change-temporary-password" verb=POST {
  api_group = "Authentication"
  auth = "user"

  input {
    password new_password filters=min:8|minAlpha:1|minDigit:1
    text confirm_password filters=trim
  }

  stack {
    db.get user {
      field_name = "id"
      field_value = $auth.id
      output = ["id", "status", "must_change_password"]
    } as $user

    precondition ($user != null && $user.status == "active") {
      error_type = "accessdenied"
      error = "Active professional account required."
    }

    precondition ($user.must_change_password == true) {
      error_type = "inputerror"
      error = "No temporary password change is pending."
    }

    precondition ($input.new_password == $input.confirm_password) {
      error_type = "inputerror"
      error = "Passwords do not match."
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
        action: "temporary_password_changed"
        metadata: {}
      }
    } as $event_log
  }

  response = {success: true}
}