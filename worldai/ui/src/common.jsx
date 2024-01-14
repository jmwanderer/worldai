import Image from 'react-bootstrap/Image';
import Carousel from 'react-bootstrap/Carousel';

function WorldImages({world}) {
  const items = world.images.map(entry =>
    <Carousel.Item key={entry.url}>
      <Image src={entry.url}
             style={{ maxWidth: "50vmin", maxHeight: "50vmin",
                      minHeight: "30vmin"}}/>
    </Carousel.Item>);
  
  return (
    <Carousel interval={null}>
      { items }
    </Carousel>            
  );
}



export { WorldImages };
