table contact {
  auth = false

  schema {
    int id
    timestamp created_at?=now
    timestamp updated_at?=now
    text name filters=trim
    text phone filters=trim
    text phone_normalized filters=trim
    enum source {
      values = ["whatsapp", "indicacao", "instagram", "ligacao", "outra"]
    }
    text notes? filters=trim
    enum status?=active {
      values = ["active", "inactive"]
    }
    timestamp first_contact_at
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "phone_normalized", op: "asc"}]}
    {type: "btree", field: [{name: "status", op: "asc"}]}
    {type: "btree", field: [{name: "source", op: "asc"}]}
    {type: "btree", field: [{name: "name", op: "asc"}]}
  ]
  guid = "kf2xOjE2P384kkHfXf9skzYBESo"
}
