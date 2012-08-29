var articles = null;

function restore_all_articles_view() {
  $("#allbtn").button('toggle');
  $('#articleslist').empty();
  $('#articleslist').append(articles);
  $('#filterwarning').hide();
}

function switch_category(category) {
  if (typeof category != "undefined") {
    $("#articleslist").empty();
    var filtered = articles.filter('.'.concat(category));
    $("#articleslist").append(filtered);
  } else {
    restore_all_articles_view();
  }
  timeandtips("#articleslist");
}

$(document).ready(function() {
  timeandtips();
  articles = $('#articleslist article');
  $('#searchfield').removeAttr("disabled");
});

$("#searchfield").keyup(function(event) {
  var text = $('#searchfield').val();
  if (text.length >= 3) {
    $("#allbtn").button('toggle');
    var found = articles.filter('article:containsi("'.concat(text, '")'));
    $('#filterwarning').show();
    $('#articleslist').empty();
    $('#articleslist').append(found);
  } else if (text.length == 0) {
    restore_all_articles_view();
  }
});
