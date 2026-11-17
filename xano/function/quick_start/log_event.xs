// Creates a record in the event log table
function "Quick Start/log_event" {
  input {
    // Unique identifier for the user who performed the action.
    int user_id
  
    // A description of the action performed by the user (e.g., 'login', 'created_invoice').
    text action
  
    // Additional data related to the event, such as resource IDs or old/new values.
    json metadata?
  }

  stack {
    db.get user {
      field_name = "id"
      field_value = $input.user_id
      output = ["barbershop_id"]
    } as $user

    function.run "Quick Start/resolve_user_barbershop" {
      input = {user_id: $input.user_id}
    } as $barbershop_scope

    // Add a new user event log entry
    db.add event_log {
      data = {
        created_at: "now"
        user_id   : $input.user_id
        barbershop_id: $barbershop_scope.barbershop_id
        action    : $input.action
        metadata  : $input.metadata
      }
    } as $new_log_entry
  }

  response = null
  tags = ["xano:quick-start"]
  guid = "-51v5srF-NFeFgK2SNsfhi5n9rg"
}