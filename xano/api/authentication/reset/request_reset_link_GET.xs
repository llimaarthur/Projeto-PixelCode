// Request a one-time magic link to reset password
query "reset/request-reset-link" verb=GET {
  api_group = "Authentication"

  input {
    email email?
  }

  stack {
    // Generate a one-time magic link
    function.run "Quick Start/generate_magic_link" {
      input = {email: $input.email}
    } as $token_and_email
  
    // Check that the link exists
    precondition ($token_and_email != null) {
      error = "Magic link could not be created. Try again."
    }
  
    // Create a variable with the API base URL
    var $api_base_url {
      value = $env.$api_baseurl
    }
  
    // Create magic link
    var $magic_link {
      value = $api_base_url
        |concat:"1_start_here_demo_page#/update-password":"/"
        |concat:$token_and_email.token:"?magic_token="
        |concat:$token_and_email.email:""
    }
  
    // Create HTML message to include magic reset password link
    util.template_engine {
      value = """
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <title>Password Reset</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
          <div style="max-width: 600px; margin: 20px auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
            <h2>Password Reset Request</h2>
            <p>Hello,</p>
            <p>We received a request to reset your password. To proceed, please click the link below:</p>
            <p style="text-align: center; margin: 30px 0;">
              <a href="{{ $var.magic_link }}" style="display: inline-block; padding: 12px 25px; background-color: #007bff; color: #ffffff; text-decoration: none; border-radius: 4px; font-size: 16px;">
                Reset Your Password
              </a>
            </p>
            <p>If you did not request a password reset, please ignore this email.</p>
            <p>Thank you.</p>
          </div>
        </body>
        </html>
        """
    } as $message
  
    // Send email with password reset link
    util.send_email {
      service_provider = "xano"
      subject = "Your password reset request"
      message = $message
    } as $send_email
  }

  response = {
    message: {}|set:"success":true|set:"message":"magic link sent"
  }

  tags = ["xano:quick-start"]
  guid = "W_s55a2hkuECCNVh4V3yLvtqnM4"
}