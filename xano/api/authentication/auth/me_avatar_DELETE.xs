// Clears the authenticated professional's Cloudinary image reference.
query "auth/me/avatar" verb=DELETE {
  api_group = "Authentication"
  auth = "user"

  input {
  }

  stack {
    function.run "Quick Start/enforce_role" {
      input = {user_id: $auth.id, required_role: "professional"}
    } as $role_check

    db.edit user {
      field_name = "id"
      field_value = $auth.id
      data = {
        profile_photo_url: ""
        profile_photo_public_id: ""
      }
    } as $updated_user
  }

  response = {
    success                 : true
    profile_photo_url       : $updated_user.profile_photo_url
    profile_photo_public_id : $updated_user.profile_photo_public_id
  }
  guid = "rEm0v3Av4t4r20261103"
}
