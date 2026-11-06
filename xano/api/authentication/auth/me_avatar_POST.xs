// Stores a Cloudinary image URL for the authenticated professional.
query "auth/me/avatar" verb=POST {
  api_group = "Authentication"
  auth = "user"

  input {
    text secure_url filters=trim
    text public_id filters=trim
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "professional"}
    } as $role_check

    precondition ($input.secure_url != "" && $input.public_id != "") {
      error_type = "inputerror"
      error = "A foto enviada não retornou dados válidos."
    }

    precondition ($input.public_id|starts_with:"lotus-barber/") {
      error_type = "inputerror"
      error = "O identificador da foto é inválido."
    }

    db.edit user {
      field_name = "id"
      field_value = $auth.id
      data = {
        profile_photo_url: $input.secure_url
        profile_photo_public_id: $input.public_id
      }
    } as $updated_user
  }

  response = {
    profile_photo_url: $updated_user.profile_photo_url
    profile_photo_public_id: $updated_user.profile_photo_public_id
  }
  guid = "DmxZyjBaT5FDdhkxeGJiUEiG0z0"
}
