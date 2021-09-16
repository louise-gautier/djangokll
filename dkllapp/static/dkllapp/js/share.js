(function() {
var supportsShare = "share" in navigator;
if (!supportsShare) {document.documentElement.classList.add("noShare");return;}
const shareData = {
title: 'Rejoins ma ligue',
text: 'Rejoins ma ligue !',
url: 'http://lgr.ddns.net:8443/rejoindre_ligue',
}
var coll = document.getElementsByClassName("share_button");
var i;
for (i = 0; i < coll.length; i++) {
  coll[i].addEventListener("click", function() {
    shareData.text = ('Rejoins ma ligue : ').concat(this.id)
    navigator.share(shareData)
});
}
})();