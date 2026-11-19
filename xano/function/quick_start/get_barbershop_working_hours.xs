// Returns the saved weekly hours, preserving the original schedule for the legacy shop.
function "Quick Start/get_barbershop_working_hours" {
  input {
    int barbershop_id
  }

  stack {
    db.get barbershop {
      field_name = "id"
      field_value = $input.barbershop_id
      output = ["id", "migration_key", "weekly_hours"]
    } as $barbershop

    precondition ($barbershop != null) {
      error_type = "inputerror"
      error = "Barbearia não encontrada."
    }

    var $weekly_hours {
      value = $barbershop.weekly_hours
    }

    conditional {
      if ($weekly_hours == null || ($weekly_hours|count) == 0) {
        conditional {
          if ($barbershop.migration_key == "legacy-default") {
            var.update $weekly_hours {
              value = [
                {day_of_week: 1, intervals: [{start_minute: 540, end_minute: 720}, {start_minute: 780, end_minute: 1140}]}
                {day_of_week: 2, intervals: [{start_minute: 540, end_minute: 720}, {start_minute: 780, end_minute: 1140}]}
                {day_of_week: 3, intervals: [{start_minute: 540, end_minute: 720}, {start_minute: 780, end_minute: 1140}]}
                {day_of_week: 4, intervals: [{start_minute: 540, end_minute: 720}, {start_minute: 780, end_minute: 1140}]}
                {day_of_week: 5, intervals: [{start_minute: 540, end_minute: 720}, {start_minute: 780, end_minute: 1140}]}
                {day_of_week: 6, intervals: [{start_minute: 540, end_minute: 840}]}
                {day_of_week: 7, intervals: []}
              ]
            }
          }
          else {
            var.update $weekly_hours {
              value = [
                {day_of_week: 1, intervals: []}
                {day_of_week: 2, intervals: []}
                {day_of_week: 3, intervals: []}
                {day_of_week: 4, intervals: []}
                {day_of_week: 5, intervals: []}
                {day_of_week: 6, intervals: []}
                {day_of_week: 7, intervals: []}
              ]
            }
          }
        }
      }
    }
  }

  response = {
    weekly_hours: $weekly_hours
  }
  guid = "w0rkH0urs7Q9m2K5vB8xC1dF"
}
