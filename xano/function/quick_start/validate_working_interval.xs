// Enforces the barbershop's weekly opening hours in its UTC-3 local time.
function "Quick Start/validate_working_interval" {
  input {
    timestamp start_at
    timestamp end_at
    json weekly_hours
  }

  stack {
    precondition ($input.start_at < $input.end_at) {
      error_type = "inputerror"
      error = "O fim do intervalo deve ser posterior ao início."
    }

    var $weekday {
      value = ($input.start_at|format_timestamp:"N":"America/Sao_Paulo")|to_int
    }

    var $start_hour {
      value = ($input.start_at|format_timestamp:"H":"America/Sao_Paulo")|to_int
    }

    var $end_hour {
      value = ($input.end_at|format_timestamp:"H":"America/Sao_Paulo")|to_int
    }

    var $start_minute {
      value = ($input.start_at|format_timestamp:"i":"America/Sao_Paulo")|to_int
    }

    var $end_minute {
      value = ($input.end_at|format_timestamp:"i":"America/Sao_Paulo")|to_int
    }

    var $start_second {
      value = ($input.start_at|format_timestamp:"s":"America/Sao_Paulo")|to_int
    }

    var $end_second {
      value = ($input.end_at|format_timestamp:"s":"America/Sao_Paulo")|to_int
    }

    var $start_minute_of_day {
      value = ($start_hour * 60) + $start_minute
    }

    var $end_minute_of_day {
      value = ($end_hour * 60) + $end_minute
    }

    precondition (
      ($input.start_at|format_timestamp:"Y-m-d":"America/Sao_Paulo")
      == ($input.end_at|format_timestamp:"Y-m-d":"America/Sao_Paulo")
    ) {
      error_type = "inputerror"
      error = "O atendimento deve começar e terminar no mesmo dia."
    }

    precondition (($start_minute == 0 || $start_minute == 30) && $start_second == 0) {
      error_type = "inputerror"
      error = "Os horários devem começar em intervalos de 30 minutos."
    }

    precondition ($end_second == 0) {
      error_type = "inputerror"
      error = "O fim do intervalo deve usar precisão de minutos."
    }

    var $inside_working_period {
      value = false
    }

    foreach ($input.weekly_hours) {
      each as day {
        conditional {
          if ($day.day_of_week == $weekday && $day.intervals != null) {
            foreach ($day.intervals) {
              each as interval {
                conditional {
                  if (
                    $start_minute_of_day >= $interval.start_minute
                    && $end_minute_of_day <= $interval.end_minute
                  ) {
                    var.update $inside_working_period {
                      value = true
                    }
                  }
                }
              }
            }
          }
        }
      }
    }

    precondition ($inside_working_period == true) {
      error_type = "inputerror"
      error = "O intervalo solicitado está fora do expediente da barbearia."
    }
  }

  response = true
  guid = "d3F8hJ1kL4mN7pQ0rT2vW5xY9aB"
}
