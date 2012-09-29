
function fadeError() {
  $("#error-modal").modal("show");
}

function voteup(oid) {
  var jqhxr = $.get("/vote/add", { "oid": oid }, function(data) {
    if (data == "nooid") {
      fadeError();
    } else {
      var cscore = $(".where_the_score_renders_for_".concat(oid)).text();
      $(".where_the_score_renders_for_".concat(oid)).empty();
      $(".where_the_score_renders_for_".concat(oid)).append(parseInt(cscore)+1);
      $(".where_the_arrow_renders_for_".concat(oid)).empty();
      $(".where_the_arrow_renders_for_".concat(oid)).append("&uarr;");
    }
  })
  .error(function() { fadeError(); });
}

function timeandtips(where) {
  var div = (where) ? where.concat(" ") : "";
  timeago = div.concat("time.timeago");
  $(timeago).timeago();
  tooltip = div.concat('a[rel=tooltip]');
  $(tooltip).tooltip();
}

function clear_search_box() {
  var text = $('#searchfield').val('');
  restore_all_articles_view();
}

// add :containsi for case insensitive :contains
jQuery.expr[":"].containsi = jQuery.expr.createPseudo(function(arg) {
  return function( elem ) {
    return jQuery(elem).text().toUpperCase().indexOf(arg.toUpperCase()) >= 0;
  };
});

// disables enter key in the searchfield
$("#searchfield").keypress(function(event) {
  if ( event.which == 13 ) {
    event.preventDefault();
  }
});
