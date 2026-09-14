// Stores logs of user activities and events within the application.
table event_log {
  auth = false

  schema {
    int id
    timestamp created_at?=now
  
    // Reference to the user who performed the action.
    int user_id? {
      table = "user"
    }
  
    // A description of the action performed by the user (e.g., 'login', 'created_invoice', 'updated_profile').
    text action? filters=trim
  
    // Additional data related to the event, such as resource IDs, old/new values, or other contextual information.
    json metadata?
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "created_at", op: "desc"}]}
  ]

  tags = ["xano:quick-start"]
  guid = "YtQuXEaMotdqqxqIk3s3fnVr6Wk"
}