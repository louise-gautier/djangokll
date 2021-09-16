var menuItems = document.getElementsByClassName("navbar-toggler2");
var i, j, k;

for (i = 0; i < menuItems.length; i++) {
  menuItems[i].addEventListener("click", function(event) {
        for (j = 0; j < menuItems.length; j++) {
            if($(event.currentTarget).attr("data-target")==$(menuItems[j]).attr("data-target")){
            }
            else{
                    menuItems[j].classList.add("collapsed");
                    list = document.getElementsByClassName("navbar-collapse")
                    for (k = 0; k < list.length; k++){
                        if("#"+$(list[k]).attr("id") == $(menuItems[j]).attr("data-target")){list[k].classList.remove("show");}
                        else{}
                    }
            }
        }
    });
}
