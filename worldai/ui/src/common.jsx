//
// React components used in design and play
//
//    Jim Wanderer
//    http://github.com/jmwanderer
//

import Image from 'react-bootstrap/Image';
import Carousel from 'react-bootstrap/Carousel';
import Navbar from 'react-bootstrap/Navbar';
import Container from 'react-bootstrap/Container';
import CloseButton from 'react-bootstrap/CloseButton';

function CloseBar({ onClose, title }) {
  return (
    <Navbar expand="lg" className="bg-body-tertiary">
      <Container>
        <Navbar.Brand>{ title }</Navbar.Brand>
        <CloseButton onClick={onClose}/>
      </Container>
    </Navbar>);
}


function WorldItem({ world, onClick }) {

  function handleClick() {
    if (onClick !== undefined && onClick !== null) {
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



function ElementImages({element}) {
  const items = element.images.map(entry =>
    <Carousel.Item key={entry.url}>
      <div className="d-flex justify-content-center">
        <Image src={entry.url}
               style={{ maxWidth: "40vmin", maxHeight: "40vmin",
                        minHeight: "25"}}/>
      </div>
    </Carousel.Item>);
  const show = element.images.length > 1;
  
  return (
    <Carousel interval={null} controls={show} indicators={show}>
      { items }
    </Carousel>            
  );
}



export { ElementImages, WorldItem, CloseBar };
