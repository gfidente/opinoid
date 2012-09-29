var articles = null;

function restore_all_articles_view() {
  $('#articleslist').empty();
  $('#articleslist').append(articles);
  $('#filterwarning').hide();
}

$(document).ready(function() {
  timeandtips();
  articles = $('#articleslist article');
  $('#searchfield').removeAttr("disabled");
});

$("#searchfield").keyup(function(event) {
  var text = $('#searchfield').val();
  if (text.length >= 3) {
    var found = articles.filter('article:containsi("'.concat(text, '")'));
    $('#filterwarning').show();
    $('#articleslist').empty();
    $('#articleslist').append(found);
  } else if (text.length == 0) {
    restore_all_articles_view();
  }
});
