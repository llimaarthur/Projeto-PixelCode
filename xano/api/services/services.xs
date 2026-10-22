// Authenticated professionals can only query active services.
query "services" verb=GET {
  api_group = "Services"
  auth = "user"

  input {
  }

  stack {
    db.query service {
      where = $db.service.status == "active"
      return = {type: "list"}
    } as $services
  }

  response = $services
  guid = "2XKel2K1YVv7Z38HrfU_AlwzyQU"
}
