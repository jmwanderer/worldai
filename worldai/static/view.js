
// Support for changing images in the element views
let image = document.getElementById("image");
let image_back = document.getElementById("image_back");
let image_fwd = document.getElementById("image_fwd");                  
let index = 0;
function setImageIndex(delta) {
    let new_index = index + delta;
    if (new_index >= 0 && new_index < images.length) {
        index = new_index;
        image.src = images[index]
    }
    image_back.disabled = (index == 0);
    image_fwd.disabled = (index == images.length - 1);
}

if (image) {
    image_back.onclick = () => setImageIndex(-1);
    image_fwd.onclick = () => setImageIndex(1);
    setImageIndex(0);
}




