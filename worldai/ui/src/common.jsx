import Image from 'react-bootstrap/Image';
import Carousel from 'react-bootstrap/Carousel';


function WorldItem({ world, onClick }) {

  function handleClick() {
    if (onClick !== null) {
      onClick(world.id);
    }
  }
  
  return (
    <div className="card mb-3 container" onClick={handleClick} >
      <div className="row">
        <div className="col-2">
          <img src={world.image.url} className="card-img" alt="world"/>
        </div>
        <div className="col-8">
          <div className="card-body">
            <h5 className="card-title">
              { world.name }
            </h5>
            <p className="card-text" style={{ textAlign: "left" }}>
              { world.description }
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

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



export { WorldImages, WorldItem };
