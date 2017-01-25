console.log('hello');
console.log($);
console.log($( '#main'));
console.log($( 'html'));
console.log($( 'html form'));
console.log($( 'form'));
console.log($( '*'));
jQuery( '#main' ).hide();
$( "#main" ).hide();
$( ".button" ).hide();
$( "#createsalad" ).hide();

$( "#createsalad" ).submit(function( event ) {
    alert("submitting");
    event.preventDefault();
});

$( "hell" )
