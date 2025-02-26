/*
Copyright (c) Facebook, Inc. and its affiliates.
*/

// src/components/LiveObjects.js

import React from "react";
import { Rnd } from "react-rnd";
import { Stage, Layer, Image as KImage, Rect, Text, Shape } from "react-konva";
import ObjectFixup from "./ObjectFixup";
import MemoryList from "./MemoryList";

const COLORS = [
  "rgba(0,200,0,.5)",
  "rgba(200,0,0,.5)",
  "rgba(0,100,255,.5)",
  "rgba(255,150,0,.5)",
  "rgba(100,255,200,.5)",
  "rgba(200,200,0,.5)",
  "rgba(0,200,150,.5)",
  "rgba(200,0,200,.5)",
  "rgba(0,204,255,.5)",
];

/**
 * Displays an image along with the object bounding boxes.
 * The object metadata and image are passed via setState.
 * Example metadata format is in the comments below.
 */
class LiveObjects extends React.Component {
  constructor(props) {
    super(props);
    this.addObject = this.addObject.bind(this);
    this.onResize = this.onResize.bind(this);
    this.onFixup = this.onFixup.bind(this);
    this.onAnnotationSave = this.onAnnotationSave.bind(this);
    this.onModelSwitch = this.onModelSwitch.bind(this);
    this.onPrevFrame = this.onPrevFrame.bind(this);
    this.onNextFrame = this.onNextFrame.bind(this);

    this.initialState = {
      height: props.height,
      width: props.width,
      scale: 1.0,
      rgb: null,
      objects: null,
      modelMetrics: null,
      offline: false,
      updateFixup: false,
      selectedObject: JSON.parse(localStorage.getItem("selected_object")),
    };
    this.state = this.initialState;
  }

  componentDidUpdate() {
    if (this.state.updateFixup) {
      this.onFixup();
      this.setState({ updateFixup: false });
    }
  }

  addObject(object) {
    let newObjects = this.state.objects
      ? this.state.objects.concat(object)
      : [object];
    this.setState({
      objects: newObjects,
    });
  }

  onResize(e, direction, ref, delta, position) {
    this.setState({
      width: parseInt(ref.style.width, 10),
      height: parseInt(ref.style.height, 10),
    });
  }

  onFixup() {
    if (this.props.stateManager) {
      let stateManager = this.props.stateManager;
      let fixer = undefined;
      stateManager.refs.forEach((ref) => {
        if (ref instanceof ObjectFixup) {
          fixer = ref;
        }
      });
      if (fixer !== undefined) {
        // Scale points
        // quad nested array: obj, masks for obj, points in mask, x/y
        let canvas_dim = 500; // hardcoded 500... not sure where this comes from
        let objects = this.state.objects.map((obj) => ({
          mask: obj.mask
            ? obj.mask.map((masks) =>
                masks.map((pt) => ({
                  x: pt[0] / canvas_dim,
                  y: pt[1] / canvas_dim,
                }))
              )
            : [],
          label: obj.label,
          properties: obj.properties.split("\n "),
          type: obj.type,
          id: obj.id,
        }));
        fixer.setState({
          image: this.state.rgb,
          objects,
        });

        var myLayout = stateManager.dashboardLayout;
        // switch the active tab in the layout to the annotation tab
        for (var i = 0; i < myLayout._getAllContentItems().length; i++) {
          if (
            myLayout._getAllContentItems()[i].config.component === "ObjectFixup"
          ) {
            var contentItem = myLayout._getAllContentItems()[i];
            contentItem.parent.setActiveContentItem(contentItem);
          }
        }
      }
    }
  }

  onAnnotationSave() {
    if (this.props.stateManager) {
      this.props.stateManager.onSave();
    }
  }

  onModelSwitch() {
    if (this.props.stateManager) {
      console.log("switching model...");
      this.props.stateManager.socket.emit("switch_detector");
    }
  }

  onPrevFrame() {
    if (this.props.stateManager) {
      this.props.stateManager.previousFrame();
    }
  }

  onNextFrame() {
    if (this.props.stateManager) {
      this.props.stateManager.nextFrame();
    }
  }

  onSelectObject(obj) {
    const currentObject = JSON.parse(localStorage.getItem("selected_object"));
    let stateManager = this.props.stateManager;
    let listObject = [];
    //get list object from MemoryList
    stateManager.refs.forEach((ref) => {
	  if (ref instanceof MemoryList) {
	    listObject = ref.state.memory.reference_objects;
	  }
	});
	 
	//change objectId in localStorage when click object
    if (currentObject && currentObject.id.toString() === obj.id.toString()) {
      this.setState({ selectedObject: null });
      localStorage.removeItem("selected_object");
    } else {
      listObject.forEach((object) => {
        const objectId = object[1]; //hardcoded by response data, not sure if data change in future
        if (objectId && objectId.toString() === obj.id.toString()) {
          const selectedValues = { uuid: object[0], id: obj.id };
          localStorage.setItem("selected_object", JSON.stringify(selectedValues));
          this.setState({ selectedObject: selectedValues });
        }
      });
    }
  }

  componentDidMount() {
    if (this.props.stateManager) this.props.stateManager.connect(this);
  }

  render() {
    const { height, width, rgb, objects } = this.state;
    const { offsetW, offsetH } = this.props;

    if (rgb === null) {
      return (
        <Rnd
          default={{
            x: offsetW,
            y: offsetH,
            width: width,
            height: height,
          }}
          lockAspectRatio={true}
          onResize={this.onResize}
        >
          <p>Loading...</p>
        </Rnd>
      );
    }

    /* example "objects": [
      {"xyz": [-0.35, -0.35, 1.35],
       "bbox": [398.8039245605469, 249.9073944091797, 424.7720642089844, 307.53729248046875],
       "label": "chair"},
      ]
    */
    var renderedObjects = [];
    let parsed_objects = objects;
    if (objects === null) {
      parsed_objects = [];
    }
    let j = 0;
    parsed_objects.forEach((obj, i) => {
      if (obj.label === "person") {
        return;
      }
      let obj_id = obj.id;
      let color_id = i;
      if (Number.isInteger(obj_id)) {
        color_id = obj_id;
      }
      let label = String(obj_id).concat("_" + obj.label);
      let properties = obj.properties;
      let color = COLORS[color_id % COLORS.length];
      let scale = this.state.scale;
      let x1 = parseInt(obj.bbox[0] * scale);
      let y1 = parseInt(obj.bbox[1] * scale);
      let x2 = parseInt(obj.bbox[2] * scale);
      let y2 = parseInt(obj.bbox[3] * scale);
      let h = y2 - y1;
      let w = x2 - x1;
      const highlightColor = "rgb(237,237,237)";
      renderedObjects.push(
        <Rect
          key={j}
          x={x1}
          y={y1}
          width={w}
          height={h}
          fillEnabled={false}
          stroke={color}
          opacity={1.0}
        />
      );
      // when object was selected, highlight it
      if (this.state.selectedObject && obj.id.toString() === this.state.selectedObject.id.toString()) {
        renderedObjects.push(
          <Rect
            key={`selected-${j}`}
            x={x1}
            y={y1}
            width={w}
            height={h}
            fillEnabled={false}
            stroke={highlightColor}
          />,
          <Text
	        key={`selected-text-${j}`}
	        text={`Selected Object: ${this.state.selectedObject.uuid}`}
	        x={5}
	        y={5}
	        fill={color}
	        fontSize={12}
	        width={this.state.width - 5}
	      />
	    );
	  }
      if (obj && obj.mask) {
        for (let j = 0; j < obj.mask.length; j++) {
          let mask = obj.mask[j].map((x) => [x[0] * scale, x[1] * scale]);
          renderedObjects.push(
            <Shape
              onClick={() => this.onSelectObject(obj)} //handle click object's mask
              sceneFunc={(context, shape) => {
                context.beginPath();
                context.moveTo(...mask[0]);
                for (let k = 1; k < mask.length; k++) {
                  context.lineTo(...mask[k]);
                }
                context.closePath();
                context.fillStrokeShape(shape);
              }}
              fill={color}
              opacity={1}
              stroke={obj.type === "detector" ? "white" : "black"}
              strokeWidth={1}
              key={`${i}-${j}`}
            />
          );
        }
      }
      renderedObjects.push(
        <Text
          key={[j++, label]}
          text={label} //.concat("\n", properties)}
          x={x1}
          y={y1}
          fill={"white"}
          opacity={1.0}
          fontSize={20}
        />
      );
    });

    let offlineButtons = null;
    if (this.state.offline) {
      offlineButtons = (
        <span style={{ float: "right" }}>
          <button onClick={this.onPrevFrame}>{"<-"}</button>
          <button onClick={this.onNextFrame}>{"->"}</button>
        </span>
      );
    }

    return (
      <Rnd
        default={{
          x: offsetW,
          y: offsetH,
          width: width,
          height: height,
        }}
        lockAspectRatio={true}
        onResize={this.onResize}
      >
        <Stage width={width} height={height}>
          <Layer>
            <KImage image={rgb} width={width} height={height} />
            {renderedObjects}
          </Layer>
        </Stage>
        <button onClick={this.onFixup}>Fix</button>
        <button onClick={this.onAnnotationSave}>Save</button>
        {offlineButtons}
      </Rnd>
    );
  }
}

export default LiveObjects;
