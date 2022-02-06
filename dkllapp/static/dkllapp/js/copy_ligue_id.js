var elem = document.getElementsByClassName("copy_id_link");
for (var i = 0; i < elem.length; i += 1) {
    (function () {
        var the_id = elem[i].name;
        elem[i].addEventListener("click", function(){
            input_objet = document.getElementById(the_id);
            input_objet.select();
            document.execCommand("copy");
        }, false);
    }());
}