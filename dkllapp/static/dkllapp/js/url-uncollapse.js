jQuery(document).ready(function()
{
    var url = document.location.toString();
    if ( url.match('#') ) {
      // exécute le gestionnaire
      var hash = url.split('#')[1]
      $('button[id='+ hash +']').addClass('active');
      $('button[id='+ hash +']').next('div').css('display', 'block')
     }
})
