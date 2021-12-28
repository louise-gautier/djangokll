console.log("coucou");
var links = document.getElementsByClassName('reply_link');
console.log("links" + links);
for(var i = 0; i < links.length; i++) {
    current_link = links[i]
    console.log("current_link " + current_link.id);
    id_div_form = parseInt(current_link.id.substring(8)).toString()
    id_div_button_reply = "reply_" + current_link.id.substring(8)

    const div_form = document.getElementById(id_div_form);
    const div_button_reply = document.getElementById(id_div_button_reply);
    console.log("id_div_form " + id_div_form);
    console.log("div_form.parentNode.style.display " + div_form.parentNode.style.display);
    const parent_display = div_form.parentNode.style.display;
    console.log("parent_display " + parent_display);

    current_link.onclick = function () {
      if (parent_display == "none") {
        console.log("parentNode if " + div_form.parentNode);
        div_form.parentNode.style.display = "flex";
        div_button_reply.style.display = "none";

      } else {
        console.log("parentNode else " + div_form.parentNode);
        div_form.style.parentNode.style.display = "none";
        div_button_reply.style.display = "flex";
      }
    }
    };