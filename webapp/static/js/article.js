var watching = null;

function get_comments_by_article_oid(oid) {
  $.get("/comments/ajax/".concat(oid), function(data) {
    $(".where_the_comments_render_for_".concat(oid)).empty();
    $(".where_the_comments_render_for_".concat(oid)).append(data);
    timeandtips(".where_the_comments_render_for_".concat(oid));
    watching = oid;
    setInterval("reload_comments()", 300000);
  });
}

function reload_comments() {
  get_comments_by_article_oid(watching);
}

function toggleReply(oid) {
  var divid = ".where_the_form_render_for_".concat(oid);
  $(divid).toggle();
  $(divid.concat(" textarea")).focus();
}

function post_form(articleid) {
  var formid = "#form_for_".concat(articleid);
  var jqhxr = $.post("/comment/add", $(formid).serialize(), function(data) {
    if (data == "noauth") {
      fadeError();
    } else if (data == "nooid") {
      fadeError();
    } else {
	$(formid).replaceWith('<p style="text-align: center;"><strong>Great.</strong></p>');
      get_comments_by_article_oid(data);
    }
  })
  .error(function() { fadeError(); });
}

$(document).ready(function() {
  var oid = $("article").attr("id");
  timeandtips();
  get_comments_by_article_oid(oid);
});
