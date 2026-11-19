// Validates the weekly schedule shape, half-hour boundaries and non-overlapping intervals.
function "Quick Start/validate_working_hours" {
  input {
    json weekly_hours
  }

  stack {
    precondition ($input.weekly_hours != null && ($input.weekly_hours|count) == 7) {
      error_type = "inputerror"
      error = "Informe os horários dos sete dias da semana."
    }

    var $valid_minutes {
      value = [
        0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330,
        360, 390, 420, 450, 480, 510, 540, 570, 600, 630, 660, 690,
        720, 750, 780, 810, 840, 870, 900, 930, 960, 990, 1020, 1050,
        1080, 1110, 1140, 1170, 1200, 1230, 1260, 1290, 1320, 1350,
        1380, 1410
      ]
    }

    var $processed_days {
      value = []
    }

    var $previous_end {
      value = -1
    }

    foreach ($input.weekly_hours) {
      each as day {
        precondition ($day.day_of_week >= 1 && $day.day_of_week <= 7) {
          error_type = "inputerror"
          error = "Um dia da semana é inválido."
        }

        array.has ($processed_days) if (`$this == $day.day_of_week`) as $duplicate_day

        precondition ($duplicate_day == false) {
          error_type = "inputerror"
          error = "Não repita dias da semana."
        }

        array.push $processed_days {
          value = $day.day_of_week
        }

        var.update $previous_end {
          value = -1
        }

        conditional {
          if ($day.intervals != null) {
            foreach ($day.intervals) {
              each as interval {
                precondition (
                  $interval.start_minute != null
                  && $interval.end_minute != null
                  && $interval.start_minute < $interval.end_minute
                  && $interval.start_minute >= $previous_end
                ) {
                  error_type = "inputerror"
                  error = "Os intervalos devem ser válidos, ordenados e sem sobreposição."
                }

                array.has ($valid_minutes) if (`$this == $interval.start_minute`) as $valid_start
                array.has ($valid_minutes) if (`$this == $interval.end_minute`) as $valid_end

                precondition ($valid_start == true && $valid_end == true) {
                  error_type = "inputerror"
                  error = "Os horários devem usar intervalos de 30 minutos."
                }

                var.update $previous_end {
                  value = $interval.end_minute
                }
              }
            }
          }
        }
      }
    }
  }

  response = true
  guid = "v4l1dH0urs7Q9m2K5vB8xC1dF"
}
