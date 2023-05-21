$( "#remove-venue" ).click(async function() {
  const venueId = $(this).data('id');
  try {
    const response = await fetch('/venues/' + venueId, {method: 'DELETE'});
    if (response.status === 200){
        window.location.href = '/';
    }
  } catch(error) {
    console.log(error)
  }
});
