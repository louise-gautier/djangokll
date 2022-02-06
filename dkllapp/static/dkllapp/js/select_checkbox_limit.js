var checkbox_event_elements = document.getElementsByClassName("form-check-input_candidat");
console.log("type1", type_choix)
var limite = 3
if ( type_choix == 1 ) {
        limite = 6
     }
console.log('limite', limite)
var theCheckboxes = document.getElementsByClassName("form-check-input_candidat");
console.log("0", "elem", theCheckboxes);
var checked_count = 0;
for (var i = 0; i < theCheckboxes.length; i += 1) {
    (function () {
        if ( theCheckboxes[i].checked ) {
            checked_count = checked_count + 1;
     }
    }());
}
console.log('checked_count', checked_count);
console.log("type1_2", type_choix)
if ( checked_count >= limite ) {
    for (var i = 0; i < theCheckboxes.length; i += 1) {
        (function () {
            if ( theCheckboxes[i].checked ) {
         }
         else
            theCheckboxes[i].disabled = true;
        }());
    }
}
else
    for (var i = 0; i < theCheckboxes.length; i += 1) {
            (function () {
                if ( theCheckboxes[i].checked ) {
             }
             else
                theCheckboxes[i].disabled = false;
            }());
    }



for (var i = 0; i < checkbox_event_elements.length; i += 1) {
    (function () {
        checkbox_event_elements[i].addEventListener("click", function(){
            var theCheckboxes = document.getElementsByClassName("form-check-input_candidat");
            console.log("0", "elem", theCheckboxes);
            var checked_count = 0;
            for (var i = 0; i < theCheckboxes.length; i += 1) {
                (function () {
                    if ( theCheckboxes[i].checked ) {
                        checked_count = checked_count + 1;
                 }
                }());
            }
            console.log('checked_count', checked_count);
            console.log("type1_2", type_choix)
            if ( checked_count >= limite ) {
                for (var i = 0; i < theCheckboxes.length; i += 1) {
                    (function () {
                        if ( theCheckboxes[i].checked ) {
                     }
                     else
                        theCheckboxes[i].disabled = true;
                    }());
                }
            }
            else
                for (var i = 0; i < theCheckboxes.length; i += 1) {
                        (function () {
                            if ( theCheckboxes[i].checked ) {
                         }
                         else
                            theCheckboxes[i].disabled = false;
                        }());
                }
        }, false);
    }());
}