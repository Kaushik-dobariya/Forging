import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.product import (
    MeasurementUnit,
    ProductCategory,
    Product,
    ProductImage,
    ProductSpecification,
)
from app.models.capability import Capability
from app.models.industry import Industry
from app.models.infrastructure import Facility, InfrastructureGallery, Equipment
from app.models.material import Material
from app.models.quality import QualitySection, Certification

# Phase 4 models
from app.models.blog import BlogPost, BlogCategory, BlogPostStatus
from app.models.case_study import CaseStudy
from app.models.faq import FAQ
from app.models.download import DownloadResource, DownloadCategory, DownloadVisibility
from app.models.setting import SiteSetting, SocialLink
from app.services.settings_service import settings_service
from app.core.logging import logger



def seed_cms_data(db: Session) -> dict:
    """
    Seeds initial industrial manufacturing CMS modules with complete,
    standardized engineering data. Idempotent check ensures existing data is preserved.
    """
    stats = {}

    # 1. Measurement Units
    units_to_seed = [
        # Weight
        ("Kilogram", "kg", "weight", 1),
        ("Metric Ton (ton)", "ton", "weight", 2),
        ("Metric Ton (MT)", "MT", "weight", 3),
        ("Pounds", "lbs", "weight", 4),
        # Length
        ("Millimeter", "mm", "length", 10),
        ("Centimeter", "cm", "length", 11),
        ("Meter", "m", "length", 12),
        ("Inch", "inch", "length", 13),
        # Capacity
        ("Tons", "Tons", "capacity", 20),
        ("Kilonewton", "kN", "capacity", 21),
        ("Metric Ton Capacity", "MT_Cap", "capacity", 22),
        ("Megapascal", "MPa", "pressure", 30),
        ("Bar", "bar", "pressure", 31),
    ]
    added_units = 0
    for name, sym, utype, order in units_to_seed:
        if not db.query(MeasurementUnit).filter(MeasurementUnit.symbol == sym).first():
            db.add(MeasurementUnit(name=name, symbol=sym, unit_type=utype, display_order=order))
            added_units += 1
    if added_units > 0:
        db.commit()
        logger.info(f"Seeded {added_units} measurement units.")
    stats["measurement_units"] = db.query(MeasurementUnit).count()

    # 2. Capabilities
    capabilities = [
            Capability(
                title="Open Die Forging",
                slug="open-die-forging",
                short_description="Custom open die free forging up to 15 MT single-piece weight with multi-directional grain flow.",
                detailed_description="Our heavy-duty open die forging presses deliver superior structural integrity, continuous grain orientation, and maximum fatigue resistance for large shafts, stepped spindles, forged blocks, and hollow cylinders.",
                hero_image="/static/images/open_die_forging.webp",
                process="Billet heating to 1250°C -> Multi-directional hydraulic press upsetting and cogging -> Grain refinement -> Annealing.",
                dimensions="Diameter up to 1,200 mm, Length up to 6,000 mm",
                capacity="Up to 15 MT single piece",
                technical_specifications="Precision tolerances according to DIN 7527 & EN 10250. Complete heat-code traceability.",
                applications="Power generation rotor shafts, marine propeller shafts, steel mill rolls, heavy press columns.",
                faqs_json=json.dumps([
                    {"question": "What is the maximum piece weight for open die forgings?", "answer": "We forge single components up to 15 Metric Tons in carbon, alloy, and stainless steel."},
                    {"question": "Are non-destructive test certificates provided?", "answer": "Yes, 100% ultrasonic testing, MPI, and mechanical test certificates are provided per EN 10204 3.1/3.2."}
                ]),
                display_order=1,
                status="published",
                meta_title="Open Die Forging Services | Heavy Industrial Components",
                meta_description="Heavy open die forgings up to 15 MT. High integrity stepped shafts, hollow forgings, and blocks engineered to international standards.",
            ),
            Capability(
                title="Closed Die Forging",
                slug="closed-die-forging",
                short_description="Precision closed die drop forging and press forging from 0.5 kg to 180 kg with tight geometric tolerances.",
                detailed_description="State-of-the-art closed-die hammer lines and automated forging presses produce near-net shape components with optimized grain flow, minimal machining allowance, and exceptional tensile strength.",
                hero_image="/static/images/closed_die_forging.webp",
                process="Induction billet heating -> Die pre-forming -> Finish impression striking -> Mechanical trimming -> Controlled cooling.",
                dimensions="Length 50 mm to 1,200 mm, Diameter 40 mm to 600 mm",
                capacity="1,000 MT to 6,300 MT mechanical & hydraulic press lines",
                technical_specifications="Tolerances adhering to EN 10243-1 Grade F & DIN 7526. Surface finish Ra 3.2 to 6.3 µm.",
                applications="Automotive crankshafts, stub axles, steering knuckles, oilfield valve bodies, railway drawbars.",
                faqs_json=json.dumps([
                    {"question": "What is the typical tooling lead time for closed die forgings?", "answer": "Tooling design and CAD/CAM simulation takes 2-3 weeks, with first article samples in 4-5 weeks."},
                    {"question": "Can you achieve near-net shape dimensions?", "answer": "Yes, our automated press forging minimizes machining stock down to 1.5 - 2.5 mm per surface."}
                ]),
                display_order=2,
                status="published",
                meta_title="Closed Die Forging Manufacturer | Near-Net Shape Components",
                meta_description="Closed die forging from 0.5 kg to 180 kg. High volume precision forging for automotive, oil & gas, and heavy machinery.",
            ),
            Capability(
                title="Ring Rolling",
                slug="ring-rolling",
                short_description="Seamless rolled rings and flanges up to 3,500 mm outer diameter with tangential grain alignment.",
                detailed_description="Advanced CNC radial-axial ring rolling machines produce high-performance seamless rings with homogeneous microstructure, superior hoop stress tolerance, and zero weld seam vulnerabilities.",
                hero_image="/static/images/ring_rolling.webp",
                process="Billet piercing and pre-form doughnut forging -> CNC radial-axial roll expansion -> Sizing -> Solution annealing / Q&T.",
                dimensions="Outer Diameter 200 mm to 3,500 mm, Height up to 800 mm",
                capacity="Radial force 250 Tons, Axial force 200 Tons",
                technical_specifications="Concentricity within 1.0 mm. ISO 14001 / PED 2014/68/EU certified production.",
                applications="Wind turbine slewing rings, pressure vessel flanges, large transmission gear blanks, aerospace bearing rings.",
                faqs_json=json.dumps([
                    {"question": "What material grades can be rolled into rings?", "answer": "We roll carbon steels, alloy steels (4140, 4340, 8620), austenitic stainless (304, 316), and duplex alloys."},
                    {"question": "What are the advantages of seamless rolled rings over fabricated rings?", "answer": "Seamless rings eliminate weld seam defects, offer uniform radial-axial strength, and reduce raw material machining waste."}
                ]),
                display_order=3,
                status="published",
                meta_title="Seamless Rolled Ring Manufacturer | CNC Ring Rolling up to 3500mm",
                meta_description="High-integrity seamless rolled rings and flanges up to 3500mm OD for energy, defence, and bearing manufacturers.",
            ),
            Capability(
                title="Precision Machining",
                slug="precision-machining",
                short_description="Turnkey CNC turning, 4-axis & 5-axis vertical machining centres (VMC) with CMM verification.",
                detailed_description="Our in-house climate-controlled machine shop offers proof machining, pre-machining, and ready-to-assemble finish machining with geometric tolerances down to ±0.008 mm.",
                hero_image="/static/images/precision_machining.webp",
                process="Rough CNC turning -> Stress relieving -> Precision 5-axis finish milling/boring -> Coordinate Measuring Machine (CMM) inspection.",
                dimensions="Turning up to Dia 1,600 mm; Milling work envelope up to 2,000 x 1,200 x 900 mm",
                capacity="Over 25 CNC turning centers and multi-axis VMCs",
                technical_specifications="Dimensional tolerances down to IT6 Grade. Surface roughness down to Ra 0.4 µm.",
                applications="Precision bevel gears, splined shafts, aerospace fittings, turbine housing mounts.",
                faqs_json=json.dumps([
                    {"question": "Do you provide CMM inspection reports with delivered parts?", "answer": "Yes, every batch includes comprehensive Zeiss CMM dimensional inspection protocols."},
                    {"question": "Can you machine hardened materials?", "answer": "Yes, we perform hard turning and milling up to 62 HRC."}
                ]),
                display_order=4,
                status="published",
                meta_title="Precision CNC Machining Services | Finished Forgings",
                meta_description="In-house CNC turning and 5-axis VMC milling for forged components. CMM verified, ready-to-assemble precision engineering.",
            ),
            Capability(
                title="Heat Treatment",
                slug="heat-treatment",
                short_description="Automated continuous & batch furnaces for normalizing, quenching & tempering (Q&T), and case hardening.",
                detailed_description="Computerized heat treatment facility calibrated to AMS 2750 & API 6A standards. Ensures target hardness, high toughness, fine grain microstructure, and minimal internal residual stress.",
                hero_image="/static/images/heat_treatment.webp",
                process="Controlled atmospheric heating -> Polymer / Water / Oil rapid quenching -> Precision tempering -> Metallographic hardness check.",
                dimensions="Furnace bed size up to 4,000 x 2,500 x 1,500 mm",
                capacity="10 MT per batch furnace charge; 50 MT daily throughput",
                technical_specifications="Temperature uniformity within ±5°C. Continuous 12-channel SCADA datalogging.",
                applications="High-strength axle shafts, fatigue-resistant gears, drill pipe tool joints, subsea mooring links.",
                faqs_json=json.dumps([
                    {"question": "Which quench mediums are available?", "answer": "We maintain agitated water, polymer, and rapid-quench oil tanks with temperature-controlled chillers."},
                    {"question": "Is your heat treatment facility API and AMS certified?", "answer": "Yes, our furnaces undergo quarterly pyrometry surveys per AMS 2750 and API Spec 6A."}
                ]),
                display_order=5,
                status="published",
                meta_title="Industrial Heat Treatment Services | Q&T, Normalizing & Annealing",
                meta_description="SCADA-controlled heat treatment plant providing normalizing, oil/polymer quenching, tempering, and solution annealing.",
            ),
            Capability(
                title="Testing & Inspection",
                slug="testing-inspection",
                short_description="NABL-accredited metallurgical lab with 1000 kN tensile UTM, Charpy impact down to -60°C, and NDT Level III.",
                detailed_description="Comprehensive in-house quality testing facility encompassing chemical spectrometry, mechanical tension/impact testing, microstructural grain size analysis, and ASNT NDT Level III certified testing.",
                hero_image="/static/images/testing_inspection.webp",
                process="Sampling -> 32-element optical spectrometry -> Universal tensile testing -> Sub-zero Charpy impact -> Ultrasonic & MPI examination.",
                dimensions="Universal testing from 1 kN to 1000 kN; Spectrometer detection down to 0.0001% elements",
                capacity="Full testing throughput supporting 100% of manufactured heats",
                technical_specifications="ISO/IEC 17025 accredited laboratory procedures. Compliance with ASTM A370, ASTM E23, ISO 6892.",
                applications="Critical aerospace forgings, offshore subsea components, pressure vessel safety fittings.",
                faqs_json=json.dumps([
                    {"question": "Can third-party inspectors witness tests at your facility?", "answer": "Yes, we regularly host TUV, DNV, Lloyd's Register, ABS, and BV third-party inspection agencies."},
                    {"question": "What is the lowest temperature for Charpy impact testing?", "answer": "Our cryogenic bath allows impact testing down to -196°C in liquid nitrogen if required."}
                ]),
                display_order=6,
                status="published",
                meta_title="Metallurgical Testing & NDT Inspection Laboratory",
                meta_description="NABL accredited quality testing laboratory: 32-channel optical emission spectro, 1000 kN UTM, low-temperature Charpy, UT & MPI.",
            ),
        ]
    added_caps = 0
    for c in capabilities:
        if not db.query(Capability).filter(Capability.slug == c.slug).first():
            db.add(c)
            added_caps += 1
    if added_caps > 0:
        db.commit()
        logger.info(f"Seeded {added_caps} capabilities.")
    stats["capabilities"] = db.query(Capability).count()

    # 3. Industries
    industries = [
            Industry(
                name="Automotive",
                slug="automotive",
                short_description="High-fatigue powertrain, suspension, and steering forgings for commercial and passenger vehicles.",
                detailed_description="Manufacturing safety-critical automotive forgings compliant with IATF 16949 standards, engineered for severe torsional loads and millions of duty cycles.",
                hero_image="/static/images/industry_automotive.webp",
                icon_image="automotive-icon",
                key_components="Crankshafts, Camshafts, Connecting Rods, Stub Axles, Steering Knuckles, Universal Joint Crosses, Crown Wheels.",
                display_order=1,
                status="published",
                meta_title="Automotive Forged Components | IATF 16949 Certified Forgings",
                meta_description="Precision automotive forgings including crankshafts, steering knuckles, and transmission gears engineered to IATF 16949 standards.",
            ),
            Industry(
                name="Oil & Gas",
                slug="oil-gas",
                short_description="High-pressure, sour-gas (NACE MR0175) compliant forgings for upstream, midstream, and subsea drilling.",
                detailed_description="Severe-service forged valves, blowout preventer (BOP) bodies, wellhead components, and heavy flanges engineered for extreme pressures up to 20,000 PSI and corrosive H2S environments.",
                hero_image="/static/images/industry_oil_gas.webp",
                icon_image="oil-gas-icon",
                key_components="Valve Bodies, Bonnet Forgings, Swivel Joints, Choke & Kill Manifolds, Subsea Wellhead Flanges, Drill Pipe Collars.",
                display_order=2,
                status="published",
                meta_title="Oil & Gas Forgings | Valve Bodies, Flanges & Subsea Components",
                meta_description="Forged oil & gas components adhering to API 6A, API 17D, and NACE MR0175 specifications for extreme pressure and offshore environments.",
            ),
            Industry(
                name="Railways",
                slug="railways",
                short_description="Heavy-haul axle forgings, coupler mechanisms, and bogie components for freight and high-speed rail.",
                detailed_description="Certified railway forgings engineered for shock resistance, cyclic impact loading, and extreme operational durability across millions of freight and passenger track kilometers.",
                hero_image="/static/images/industry_railways.webp",
                icon_image="railway-icon",
                key_components="Locomotive Axles, Center Buffer Couplers (CBC), Draft Gear Forgings, Wheel Centers, Brake Beam Levers.",
                display_order=3,
                status="published",
                meta_title="Railway Forgings | Locomotive Axles & Coupler Components",
                meta_description="Heavy rail forgings meeting AAR and UIC railway standards. Locomotive axles, draft gear knuckles, and bogie components.",
            ),
            Industry(
                name="Power Generation",
                slug="power-generation",
                short_description="Turbine rotor shafts, generator retaining rings, and nuclear-grade forged fittings for energy plants.",
                detailed_description="Critical forged components for thermal, hydro, nuclear, and wind energy installations with strict creep resistance and high-temperature metallurgical stability.",
                hero_image="/static/images/industry_power_gen.webp",
                icon_image="power-icon",
                key_components="Steam Turbine Rotor Shafts, Hydro Pelton Runners, Wind Gearbox Rolled Rings, Generator Shafts, Nuclear Valve Forgings.",
                display_order=4,
                status="published",
                meta_title="Power Generation Forgings | Steam Turbine Shafts & Wind Rings",
                meta_description="Forgings for thermal, hydroelectric, and renewable energy sectors. Creep-resistant turbine rotors and wind slewing rings.",
            ),
            Industry(
                name="Agriculture",
                slug="agriculture",
                short_description="Rugged tillage tools, tractor driveline yokes, and combine harvester transmission forgings.",
                detailed_description="Abrasion-resistant and shock-absorbing forged parts built to endure rock impacts, heavy field compaction, and non-stop seasonal harvesting.",
                hero_image="/static/images/industry_agriculture.webp",
                icon_image="agriculture-icon",
                key_components="Tractor Spindles, PTO Driveline Yokes, Rotary Tiller Blades, Cultivator Shanks, Final Drive Bull Gears.",
                display_order=5,
                status="published",
                meta_title="Agricultural Equipment Forgings | Tractor Driveline & Tillage",
                meta_description="Durable forged components for agricultural machinery, tractors, and combine harvesters with high wear resistance.",
            ),
            Industry(
                name="Construction",
                slug="construction",
                short_description="Earthmoving bucket teeth, hydraulic cylinder clevises, and crane hook forgings for extreme loads.",
                detailed_description="High-strength alloy forgings designed for excavators, wheel loaders, motor graders, and mobile cranes operating in abrasive environments.",
                hero_image="/static/images/industry_construction.webp",
                icon_image="construction-icon",
                key_components="Excavator Track Links, Hydraulic Cylinder Clevises, Crane Lifting Hooks, Ripper Shanks, Bull Gear Pinions.",
                display_order=6,
                status="published",
                meta_title="Construction & Earthmoving Forgings | Heavy Machinery Parts",
                meta_description="Wear-resistant forged components for construction equipment, earthmovers, and mining machinery.",
            ),
            Industry(
                name="Heavy Engineering",
                slug="heavy-engineering",
                short_description="Custom open die forged columns, tie rods, roll mandrels, and pinion shafts for industrial plants.",
                detailed_description="Large-scale forgings for steel rolling mills, cement kilns, sugar plants, and mechanical press builders needing multi-ton structural strength.",
                hero_image="/static/images/industry_heavy_eng.webp",
                icon_image="heavy-eng-icon",
                key_components="Mill Drive Spindles, Hydraulic Tie Rods, Forged Press Cylinders, Trunnion Bearings, Kiln Roller Shafts.",
                display_order=7,
                status="published",
                meta_title="Heavy Engineering Forgings | Mill Spindles & Press Columns",
                meta_description="Large-format forgings up to 15 MT for steel mills, cement plants, and heavy manufacturing machinery.",
            ),
            Industry(
                name="Industrial Machinery",
                slug="industrial-machinery",
                short_description="High-speed gearbox shafts, fluid power pump blocks, and compressor eccentric shafts.",
                detailed_description="Precision-balanced forged shafts and structural housings for industrial blowers, process compressors, reduction gearboxes, and plastic injection machines.",
                hero_image="/static/images/industry_machinery.webp",
                icon_image="machinery-icon",
                key_components="Gearbox Input/Output Shafts, Compressor Crankshafts, Pump Manifolds, Cam Discs, Couplings.",
                display_order=8,
                status="published",
                meta_title="Industrial Machinery Forgings | Gearbox Shafts & Manifolds",
                meta_description="High-precision forged blanks and finished machined components for pumps, compressors, and industrial reduction gearboxes.",
            ),
            Industry(
                name="Defence",
                slug="defence",
                short_description="Tactical vehicle suspension arms, artillery barrel blanks, and naval grade forged fittings.",
                detailed_description="Ultra-high-strength forged components adhering to stringent military standards (MIL-SPEC) with certified ballistic and low-temperature impact properties.",
                hero_image="/static/images/industry_defence.webp",
                icon_image="defence-icon",
                key_components="Armored Vehicle Torsion Bars, Heavy Suspension Control Arms, Naval Propulsion Shafts, Gun Cradle Mounts.",
                display_order=9,
                status="published",
                meta_title="Defence & Military Forgings | Armored Vehicle & Naval Parts",
                meta_description="Mission-critical defence forgings manufactured under strict quality and traceability protocols to MIL-STD specifications.",
            ),
        ]
    added_inds = 0
    for ind in industries:
        if not db.query(Industry).filter(Industry.slug == ind.slug).first():
            db.add(ind)
            added_inds += 1
    if added_inds > 0:
        db.commit()
        logger.info(f"Seeded {added_inds} industries.")
    stats["industries"] = db.query(Industry).count()

    # 4. Equipment
    equipment_list = [
            Equipment(
                name="Hydraulic Die Forging Press 4000 MT",
                category="Hydraulic Press",
                manufacturer="Schuler / Siempelkamp",
                model="HDP-4000",
                capacity="4,000 Metric Tons",
                specifications="Stroke: 1,400 mm | Bed Area: 2,500 x 2,000 mm | Max Daylight: 2,800 mm | Fast closing speed: 300 mm/s",
                description="Heavy multi-stage closed-die hydraulic press equipped with CNC die shuttle and computerized stroke velocity regulation.",
                image="/static/images/equipment_hydraulic_press.webp",
                status="published",
                display_order=1,
            ),
            Equipment(
                name="High-Speed Mechanical Forging Press 2500 MT",
                category="Mechanical Press",
                manufacturer="Aida Engineering",
                model="CFP-2500",
                capacity="2,500 Metric Tons",
                specifications="Continuous strokes: 45 spm | Bolster size: 1,600 x 1,400 mm | Automated robotic billet feeder",
                description="High-throughput mechanical crank press optimized for automotive crankshafts and suspension components.",
                image="/static/images/equipment_mechanical_press.webp",
                status="published",
                display_order=2,
            ),
            Equipment(
                name="Friction Drop Hammer 3 Ton",
                category="Drop Hammer",
                manufacturer="Bêché & Grohs",
                model="FDH-3000",
                capacity="3,000 kg Tup Weight",
                specifications="Blow energy: 85 kJ | Max stroke: 1,500 mm | Forging rate: 60-80 blows/min",
                description="Double-frame friction drop hammer ideal for intricate closed-die impressions and close-tolerance gear forgings.",
                image="/static/images/equipment_drop_hammer.webp",
                status="published",
                display_order=3,
            ),
            Equipment(
                name="Heavy Duty CNC Horizontal Turning Center",
                category="CNC Turning",
                manufacturer="Doosan / DN Solutions",
                model="PUMA 5100LY",
                capacity="Dia 650 mm x 2,000 mm Length",
                specifications="Max turning dia: 650 mm | Spindle bore: 165 mm | Live tooling BMT 75 | Y-axis travel: ±100 mm",
                description="Heavy slant-bed lathe with programmable tailstock and driven rotary tools for complete one-setup turning and milling.",
                image="/static/images/equipment_cnc_turning.webp",
                status="published",
                display_order=4,
            ),
            Equipment(
                name="5-Axis Vertical Machining Center (VMC)",
                category="CNC VMC",
                manufacturer="Mazak",
                model="Variaxis i-800",
                capacity="Table Dia 800 mm, Load 1,000 kg",
                specifications="Spindle: 18,000 RPM HSK-A100 | X/Y/Z travel: 730/850/560 mm | Tool magazine: 60 stations",
                description="High-precision simultaneous 5-axis machining center for complex aerodynamic and fluid valve contouring.",
                image="/static/images/equipment_cnc_vmc.webp",
                status="published",
                display_order=5,
            ),
            Equipment(
                name="Continuous Gas-Fired Heat Treatment Line",
                category="Heat Treatment Furnace",
                manufacturer="Ipsen Industrial",
                model="HTF-Series Continuous",
                capacity="3.5 Tons / Hour throughput",
                specifications="Max Temp: 1,150°C | Accuracy: ±3°C | Dual quench tank (water & agitated polymer) with automatic elevator",
                description="SCADA-automated roller hearth furnace line providing normalizing, hardening, quenching, and tempering in inert atmosphere.",
                image="/static/images/equipment_furnace.webp",
                status="published",
                display_order=6,
            ),
            Equipment(
                name="Optical Emission Spectrometer 32-Channel",
                category="Spectrometer",
                manufacturer="Thermo Fisher Scientific",
                model="ARL iSpark 8860",
                capacity="Full elemental analysis down to 1 ppm",
                specifications="32 analytical channels covering C, S, P, N, O, Cr, Ni, Mo, V, Ti, Al, B, and tramp elements",
                description="High-resolution PMT spectrometer for rapid 15-second melt verification and positive material identification (PMI).",
                image="/static/images/equipment_spectrometer.webp",
                status="published",
                display_order=7,
            ),
            Equipment(
                name="Digital Ultrasonic Flaw Detector",
                category="UT Machine",
                manufacturer="Olympus / Evident",
                model="OmniScan X3 64:128PR",
                capacity="Phased Array UT & TOFD Inspection",
                specifications="64/128 channels | Frequency range: 0.2 to 26.5 MHz | Automated encoded scanning with real-time sectorial scan",
                description="Advanced Phased Array Ultrasonic Testing unit ensuring 100% volumetric subsurface defect detection.",
                image="/static/images/equipment_ut_machine.webp",
                status="published",
                display_order=8,
            ),
            Equipment(
                name="Computerized Universal Testing Machine 1000 kN",
                category="Testing Equipment",
                manufacturer="Instron",
                model="UTM-1000HD",
                capacity="1,000 kN (100 Tons Tensile / Compressive)",
                specifications="Load measurement accuracy: Class 0.5 | Servo-hydraulic control | High-temperature furnace attachment up to 900°C",
                description="Determines tensile yield strength (0.2% offset), ultimate tensile strength, elongation percentage, and area reduction.",
                image="/static/images/equipment_utm.webp",
                status="published",
                display_order=9,
            ),
        ]
    added_eq = 0
    for eq in equipment_list:
        if not db.query(Equipment).filter(Equipment.name == eq.name).first():
            db.add(eq)
            added_eq += 1
    if added_eq > 0:
        db.commit()
        logger.info(f"Seeded {added_eq} equipment items.")
    stats["equipment"] = db.query(Equipment).count()

    # 5. Facilities & Gallery
    facilities = [
            Facility(
                name="Main Heavy Forge Plant",
                category="Forge Shop",
                description="Housing our 4000 MT hydraulic press, 2500 MT mechanical press lines, and 3-ton drop hammers with automated induction heating.",
                capacity="45,000 Metric Tons Annual Forging Capacity",
                specifications="Covered Area: 120,000 sq ft | 3 Overhead EOT Cranes (up to 30 MT load) | Green-energy solar roof integration",
                image="/static/images/facility_forge_shop.webp",
                display_order=1,
                status="published",
            ),
            Facility(
                name="Climate-Controlled CNC Machine Shop",
                category="Machining Centre",
                description="Advanced proof and finish machining hall featuring over 30 CNC turning centers, vertical boring mills, and 5-axis machining centers.",
                capacity="250,000 Machined Components / Month",
                specifications="Temperature regulated at 20°C ± 1°C | In-house tooling pre-setter | Automated swarf evacuation and coolant filtration",
                image="/static/images/facility_machining.webp",
                display_order=2,
                status="published",
            ),
            Facility(
                name="SCADA Automated Heat Treatment Division",
                category="Heat Treatment Plant",
                description="Multi-line continuous and batch heat treatment setup compliant with AMS 2750 pyrometry standards and API 6A protocols.",
                capacity="60 MT Daily Heat Treatment Capacity",
                specifications="4 Roller Hearth Furnaces | 2 Drop-Bottom Solution Annealing Furnaces | 120,000-liter polymer & oil quench tanks",
                image="/static/images/facility_heat_treatment.webp",
                display_order=3,
                status="published",
            ),
            Facility(
                name="NABL Accredited Quality & Metallurgy Centre",
                category="Metallurgical Lab",
                description="World-class testing facility housing optical emission spectrometers, wet chemistry, 1000 kN tensile UTMs, and NDT inspection bays.",
                capacity="100% Heat-by-Heat Verification",
                specifications="ISO/IEC 17025 accredited | ASNT Level III NDT team | Cryogenic Charpy impact testing down to -196°C",
                image="/static/images/facility_lab.webp",
                display_order=4,
                status="published",
            ),
    ]

    infra_gallery = [
        InfrastructureGallery(
            title="4000 MT Press Billet De-scaling",
            category="Shop Floor",
            image_url="/static/images/gallery_1.webp",
            caption="High-pressure water de-scaling before finish die impression.",
            display_order=1,
        ),
        InfrastructureGallery(
            title="CNC 5-Axis VMC Machining Impeller",
            category="Machinery",
            image_url="/static/images/gallery_2.webp",
            caption="Simultaneous 5-axis finish profiling on high-alloy steel.",
            display_order=2,
        ),
        InfrastructureGallery(
            title="Continuous Quenching Elevator Cycle",
            category="Heat Treatment",
            image_url="/static/images/gallery_3.webp",
            caption="Rapid automated transfer into agitated polymer quench bath.",
            display_order=3,
        ),
        InfrastructureGallery(
            title="Zeiss CMM Precision Coordinate Verification",
            category="Quality Lab",
            image_url="/static/images/gallery_4.webp",
            caption="Sub-micron 3D spatial coordinate verification of critical spline gears.",
            display_order=4,
        ),
    ]
    added_fac = 0
    for fac in facilities:
        if not db.query(Facility).filter(Facility.name == fac.name).first():
            db.add(fac)
            added_fac += 1
    for item in infra_gallery:
        if not db.query(InfrastructureGallery).filter(InfrastructureGallery.title == item.title).first():
            db.add(item)
            added_fac += 1
    if added_fac > 0:
        db.commit()
        logger.info("Seeded facilities and gallery items.")
    stats["facilities"] = db.query(Facility).count()

    # 6. Materials
    materials = [
            Material(
                name="Carbon Steel",
                slug="carbon-steel",
                grade="AISI 1020, 1045, EN8, EN9, C45, ASTM A105",
                standard="ASTM, EN, DIN, IS, JIS",
                chemical_composition="C: 0.42-0.50% | Mn: 0.60-0.90% | Si: 0.15-0.35% | P: <=0.035% | S: <=0.035%",
                mechanical_properties="Tensile: 600-750 MPa | Yield: >=350 MPa | Elongation: >=16% | Hardness: 180-220 HB",
                applications="Automotive transmission shafts, agricultural hubs, general machinery brackets, forged pipe flanges.",
                description="Versatile plain carbon steels offering excellent machinability, weldability, and through-hardening for moderately stressed components.",
                image="/static/images/material_carbon_steel.webp",
                display_order=1,
                status="published",
                meta_title="Carbon Steel Forging Grades | AISI 1045, EN8, ASTM A105",
                meta_description="Carbon steel forging specifications, chemical analysis, and mechanical properties for automotive and general engineering.",
            ),
            Material(
                name="Alloy Steel",
                slug="alloy-steel",
                grade="AISI 4140, 4340, 8620, EN19, EN24, 42CrMo4",
                standard="ASTM, EN, DIN, ISO",
                chemical_composition="C: 0.38-0.45% | Cr: 0.90-1.20% | Mo: 0.15-0.30% | Mn: 0.60-0.90% | Ni: (Optional in 4340 up to 2.0%)",
                mechanical_properties="Tensile: 850-1000 MPa | Yield: >=680 MPa | Impact (Charpy-V): >=35 J at -20°C | Hardness: 260-320 HB",
                applications="High-torque crankshafts, heavy-duty stub axles, oilfield drill collars, high-pressure BOP valve forgings.",
                description="Chromium-molybdenum high-strength alloy steels providing superior fatigue resistance, deep hardenability, and shock toughness.",
                image="/static/images/material_alloy_steel.webp",
                display_order=2,
                status="published",
                meta_title="Alloy Steel Forging Materials | 4140, 4340, EN19, EN24",
                meta_description="High-strength alloy steel forgings for extreme torsional and impact applications. Complete heat treat and mechanical data.",
            ),
            Material(
                name="Stainless Steel",
                slug="stainless-steel",
                grade="SS 304, 304L, 316, 316L, 17-4PH, F51 Duplex 2205",
                standard="ASTM A182, EN 10088, DIN 17440",
                chemical_composition="Cr: 16.0-18.5% | Ni: 10.0-14.0% | Mo: 2.0-3.0% | C: <=0.03% | N: 0.14-0.20% (Duplex)",
                mechanical_properties="Tensile: 550-800 MPa | Yield: >=240 MPa (Austenitic) / >=450 MPa (Duplex) | Elongation: >=30%",
                applications="Subsea offshore connectors, pharmaceutical pump bodies, chemical reactors, food processing equipment.",
                description="Austenitic, martensitic, and duplex stainless steel forgings offering supreme pitting and crevice corrosion resistance in aggressive environments.",
                image="/static/images/material_stainless_steel.webp",
                display_order=3,
                status="published",
                meta_title="Stainless Steel Forging Manufacturer | SS316L, 17-4PH, Duplex 2205",
                meta_description="Corrosion-resistant stainless and duplex steel forgings compliant with ASTM A182 and NACE MR0175.",
            ),
            Material(
                name="EN Series Steel",
                slug="en-series-steel",
                grade="EN8D, EN19, EN24, EN31, EN36C",
                standard="BS 970, EN 10083",
                chemical_composition="Standardized European alloy formulations optimized for carburizing, case hardening, and through-hardening.",
                mechanical_properties="Tensile: 700-1200 MPa dependent on tempering profile | Hardness: up to 62 HRC post-case hardening.",
                applications="Precision gear blanks, heavy roller bearing rings, transmission pinions, high-tensile fasteners.",
                description="Extensively utilized British and European standard engineering steels engineered for extreme surface wear and contact fatigue resistance.",
                image="/static/images/material_en_series.webp",
                display_order=4,
                status="published",
                meta_title="EN Series Engineering Steel Forgings | EN8, EN19, EN24, EN31",
                meta_description="EN series forged steels for gears, shafts, and bearing rings according to BS 970 and EN 10083 specifications.",
            ),
            Material(
                name="Special Alloys",
                slug="special-alloys",
                grade="Inconel 718, Inconel 625, Monel 400, Hastelloy C-276, Titanium Gr 5",
                standard="AMS 5662, ASTM B637, NACE MR0175",
                chemical_composition="Ni-base superalloys with Cr, Mo, Nb, and Ti precipitations engineered for 650°C+ service.",
                mechanical_properties="Yield Strength >= 1030 MPa at room temp | High creep-rupture strength at elevated temperatures.",
                applications="Aerospace jet engine disks, nuclear reactor internal fittings, subsea sour-well completion equipment.",
                description="Nickel and titanium superalloys manufactured under vacuum induction melting (VIM-VAR) protocols for extreme aerospace and chemical environments.",
                image="/static/images/material_special_alloys.webp",
                display_order=5,
                status="published",
                meta_title="Nickel Superalloy & Titanium Forgings | Inconel 718, Monel 400",
                meta_description="High-temperature superalloy forgings for aerospace, nuclear, and severe sour-gas applications.",
            ),
            Material(
                name="Custom Materials",
                slug="custom-materials",
                grade="Proprietary Micro-Alloyed Forging Steels (Vanadium / Niobium treated)",
                standard="Customer Specific OEM Engineering Standards",
                chemical_composition="Tailored chemistries with ultra-low residual sulfur (<=0.005%) and controlled inclusion cleanliness.",
                mechanical_properties="Custom optimized yield, elongation, and low-temperature impact combinations.",
                applications="Bespoke OEM projects, high-stress lightweight automotive chassis links, prototype machinery.",
                description="In collaboration with premier steel mills, we develop tailored alloy chemistries formulated to meet exact engineering specifications.",
                image="/static/images/material_custom.webp",
                display_order=6,
                status="published",
                meta_title="Custom Micro-Alloyed Steel Forgings | Tailored OEM Grades",
                meta_description="Custom metallurgical design and micro-alloyed forging steels engineered to unique customer specifications.",
            ),
        ]
    added_mat = 0
    for mat in materials:
        if not db.query(Material).filter(Material.slug == mat.slug).first():
            db.add(mat)
            added_mat += 1
    if added_mat > 0:
        db.commit()
        logger.info(f"Seeded {added_mat} materials.")
    stats["materials"] = db.query(Material).count()

    # 7. Quality Sections
    quality_sections = [
            QualitySection(
                section_key="policy",
                title="Quality Policy & Corporate Commitment",
                subtitle="Zero-Defect Engineering Culture",
                content="We are committed to delivering precision-forged and machined components that consistently surpass customer specifications, international regulatory standards, and statutory requirements. Our quality management system prioritizes defect prevention, continuous cycle-time reduction, complete material traceability, and sustainable manufacturing practices.",
                display_order=1,
                is_active=True,
            ),
            QualitySection(
                section_key="qms",
                title="Quality Management System (QMS)",
                subtitle="Integrated ISO 9001:2015 & IATF 16949 Framework",
                content="Our QMS operates on a closed-loop PDCA (Plan-Do-Check-Act) architecture. From Advanced Product Quality Planning (APQP) and Failure Mode and Effects Analysis (FMEA) to Production Part Approval Process (PPAP Level 3/5), every manufacturing variable is instrumented, monitored, and analyzed via statistical process control (SPC).",
                display_order=2,
                is_active=True,
            ),
            QualitySection(
                section_key="inspection",
                title="Inspection & Non-Destructive Testing (NDT)",
                subtitle="ASNT Level III Supervised In-Line Verification",
                content="Non-destructive testing protocols guarantee volumetric soundness and surface integrity without compromising component geometry. Our certified inspectors execute 100% Magnetic Particle Inspection (MPI) for surface cracking, Phased Array Ultrasonic Testing (PAUT) for internal voids or inclusions, and Liquid Penetrant Testing (LPT) on all stainless and non-ferrous forgings.",
                display_order=3,
                is_active=True,
            ),
            QualitySection(
                section_key="testing",
                title="Testing Facilities & Metallurgical Laboratories",
                subtitle="NABL / ISO 17025 Compliant Chemical & Mechanical Labs",
                content="Our laboratory is equipped with state-of-the-art diagnostic instruments: a 32-channel Optical Emission Spectrometer for elemental verification, 1000 kN computerized Universal Tensile Testing machines, Charpy V-notch impact testers capable of sub-zero cryogenic testing down to -196°C, Vickers/Rockwell hardness testing, and inverted metallurgical microscopes for grain size analysis (ASTM E112).",
                display_order=4,
                is_active=True,
            ),
            QualitySection(
                section_key="traceability",
                title="Material Traceability & Heat-Code Integrity",
                subtitle="100% Cradle-to-Grave Digital Traceability",
                content="Every forged billet is assigned a permanent unique identification heat code directly tracked in our ERP. Positive Material Identification (PMI) is performed upon billet receipt, at hot forging exit, post-heat treatment, and prior to final dispatch. Test certificates conform to EN 10204 Type 3.1 and 3.2 with dual inspection endorsement.",
                display_order=5,
                is_active=True,
            ),
            QualitySection(
                section_key="standards",
                title="International Standards & Compliance",
                subtitle="Adherence to Global Engineering Norms",
                content="Our engineering and quality inspection protocols strictly align with major global governing standards: ASTM (A105, A182, A350, A668), ASME Boiler and Pressure Vessel Code (Section II & VIII), DIN EN (10222, 10250, 10083), API (Spec 6A, 16A, 17D), NACE MR0175 / ISO 15156 for sour oilfield environments, and AAR/UIC for railway applications.",
                display_order=6,
                is_active=True,
            ),
            QualitySection(
                section_key="qa_process",
                title="Quality Assurance Lifecycle Process",
                subtitle="Six-Gate Zero Defect Manufacturing Methodology",
                content="Gate 1: Raw Material Verification (Spectro, UT & macro-etching) -> Gate 2: Die & Tooling CMM Verification -> Gate 3: First Piece Hot Inspection (Pyrometry & optical dimensioning) -> Gate 4: In-Process Statistical Control & Heat Treatment Hardness Surveys -> Gate 5: 100% Volumetric NDT & Proof Machining Inspection -> Gate 6: Pre-Dispatch Quality Audit, Anti-Rust Preservation & Packaging Validation.",
                display_order=7,
                is_active=True,
            ),
        ]
    added_qs = 0
    for qs in quality_sections:
        if not db.query(QualitySection).filter(QualitySection.section_key == qs.section_key).first():
            db.add(qs)
            added_qs += 1
    if added_qs > 0:
        db.commit()
        logger.info(f"Seeded {added_qs} quality sections.")
    stats["quality_sections"] = db.query(QualitySection).count()

    # 8. Certifications
    certifications = [
            Certification(
                certificate_name="ISO 9001:2015 Quality Management System",
                issuing_organization="TÜV NORD CERT GmbH",
                certificate_number="01 100 14352",
                issue_date="2023-04-15",
                expiry_date="2026-04-14",
                description="Certification for design, closed die forging, open die forging, heat treatment, and precision machining of carbon, alloy, and stainless steel engineering components.",
                certificate_image="/static/images/cert_iso_9001.webp",
                certificate_pdf="/uploads/general/iso_9001_certificate.pdf",
                display_order=1,
                status="published",
            ),
            Certification(
                certificate_name="IATF 16949:2016 Automotive Quality Certification",
                issuing_organization="Lloyd's Register Quality Assurance",
                certificate_number="IATF-0394821",
                issue_date="2023-08-10",
                expiry_date="2026-08-09",
                description="Comprehensive automotive standard certification covering manufacturing of critical forged powertrain, steering, and suspension components.",
                certificate_image="/static/images/cert_iatf_16949.webp",
                certificate_pdf="/uploads/general/iatf_16949_certificate.pdf",
                display_order=2,
                status="published",
            ),
            Certification(
                certificate_name="PED 2014/68/EU Pressure Equipment Directive",
                issuing_organization="BSI Group The Netherlands B.V.",
                certificate_number="CE-PED-98124",
                issue_date="2024-01-20",
                expiry_date="2027-01-19",
                description="Approval of material manufacturer under European Pressure Equipment Directive 2014/68/EU Annex I Section 4.3 for pressure vessel forgings.",
                certificate_image="/static/images/cert_ped.webp",
                certificate_pdf="/uploads/general/ped_certificate.pdf",
                display_order=3,
                status="published",
            ),
            Certification(
                certificate_name="ISO 14001:2015 Environmental Management System",
                issuing_organization="Bureau Veritas Certification",
                certificate_number="IND-ENV-7721",
                issue_date="2023-11-05",
                expiry_date="2026-11-04",
                description="Certification of environmental sustainability, energy efficiency, waste minimization, and emissions compliance in heavy industrial forging.",
                certificate_image="/static/images/cert_iso_14001.webp",
                certificate_pdf="/uploads/general/iso_14001_certificate.pdf",
                display_order=4,
                status="published",
            ),
            Certification(
                certificate_name="AS9100D / EN 9100 Aerospace Quality System",
                issuing_organization="DNV GL Business Assurance",
                certificate_number="AS-2024-883",
                issue_date="2024-05-12",
                expiry_date="2027-05-11",
                description="Aerospace sector certification for the manufacture of structural alloy and titanium forgings for aviation and defence equipment.",
                certificate_image="/static/images/cert_as9100.webp",
                certificate_pdf="/uploads/general/as9100_certificate.pdf",
                display_order=5,
                status="published",
            ),
        ]
    added_cert = 0
    for cert in certifications:
        if not db.query(Certification).filter(Certification.certificate_name == cert.certificate_name).first():
            db.add(cert)
            added_cert += 1
    if added_cert > 0:
        db.commit()
        logger.info(f"Seeded {added_cert} certifications.")
    stats["certifications"] = db.query(Certification).count()

    # 9. Product Categories
    categories = [
            ProductCategory(
                name="Closed Die Forgings",
                slug="closed-die-forgings",
                description="Near-net shape closed-die components engineered for automotive, rail, and heavy equipment with continuous grain flow.",
                image="/static/images/cat_closed_die.webp",
                display_order=1,
                is_active=True,
                meta_title="Closed Die Forgings Catalog | Precision Engineered Components",
                meta_description="Explore our closed die forgings catalog from 1 kg to 180 kg: crankshafts, axles, gear blanks, and valve bodies.",
            ),
            ProductCategory(
                name="Open Die Forgings",
                slug="open-die-forgings",
                description="Heavy open-die stepped shafts, forged discs, cylinders, and blocks up to 15 MT for marine, energy, and heavy engineering.",
                image="/static/images/cat_open_die.webp",
                display_order=2,
                is_active=True,
                meta_title="Open Die Forged Shafts & Blocks Catalog | Up to 15 MT",
                meta_description="Heavy open-die forged shafts, spindles, rolls, and blocks manufactured in carbon, alloy, and stainless steels.",
            ),
            ProductCategory(
                name="Rolled Rings & Flanges",
                slug="rolled-rings-flanges",
                description="High-integrity seamless rolled rings, slewing rings, and high-pressure flanges up to 3500 mm outer diameter.",
                image="/static/images/cat_rolled_rings.webp",
                display_order=3,
                is_active=True,
                meta_title="Seamless Rolled Rings & Forged Flanges Catalog",
                meta_description="Seamless rolled rings up to 3.5m OD for wind turbines, bearings, pressure vessels, and aerospace applications.",
            ),
            ProductCategory(
                name="Precision Machined Components",
                slug="precision-machined-components",
                description="Ready-to-assemble CNC turned and 5-axis milled precision components with strict dimensional and surface tolerances.",
                image="/static/images/cat_machined.webp",
                display_order=4,
                is_active=True,
                meta_title="Precision Machined Forgings | Ready-to-Assemble Parts",
                meta_description="Finished CNC machined forgings verified on coordinate measuring machines (CMM) with sub-micron precision.",
            ),
        ]
    added_cats = 0
    for cat in categories:
        if not db.query(ProductCategory).filter(ProductCategory.slug == cat.slug).first():
            db.add(cat)
            added_cats += 1
    if added_cats > 0:
        db.commit()
        logger.info(f"Seeded {added_cats} product categories.")
    stats["categories"] = db.query(ProductCategory).count()

    # 10. Products & Specifications & Relationships
    existing_crank = db.query(Product).filter(Product.slug == "forged-heavy-duty-crankshaft").first()
    if not existing_crank:
        cat_closed = db.query(ProductCategory).filter(ProductCategory.slug == "closed-die-forgings").first()
        cat_open = db.query(ProductCategory).filter(ProductCategory.slug == "open-die-forgings").first()
        cat_rings = db.query(ProductCategory).filter(ProductCategory.slug == "rolled-rings-flanges").first()
        cat_machined = db.query(ProductCategory).filter(ProductCategory.slug == "precision-machined-components").first()

        cap_open = db.query(Capability).filter(Capability.slug == "open-die-forging").first()
        cap_closed = db.query(Capability).filter(Capability.slug == "closed-die-forging").first()
        cap_rings = db.query(Capability).filter(Capability.slug == "ring-rolling").first()
        cap_machining = db.query(Capability).filter(Capability.slug == "precision-machining").first()
        cap_heat = db.query(Capability).filter(Capability.slug == "heat-treatment").first()
        cap_test = db.query(Capability).filter(Capability.slug == "testing-inspection").first()

        ind_auto = db.query(Industry).filter(Industry.slug == "automotive").first()
        ind_oil = db.query(Industry).filter(Industry.slug == "oil-gas").first()
        ind_rail = db.query(Industry).filter(Industry.slug == "railways").first()
        ind_power = db.query(Industry).filter(Industry.slug == "power-generation").first()
        ind_heavy = db.query(Industry).filter(Industry.slug == "heavy-engineering").first()

        mat_alloy = db.query(Material).filter(Material.slug == "alloy-steel").first()
        mat_carbon = db.query(Material).filter(Material.slug == "carbon-steel").first()
        mat_stainless = db.query(Material).filter(Material.slug == "stainless-steel").first()

        eq_press = db.query(Equipment).filter(Equipment.name.like("%Hydraulic%")).first()
        eq_lathe = db.query(Equipment).filter(Equipment.name.like("%CNC Horizontal%")).first()
        eq_furnace = db.query(Equipment).filter(Equipment.name.like("%Heat Treatment%")).first()

        # Product 1: Forged Crankshaft
        p1 = Product(
            name="Forged Heavy-Duty Crankshaft",
            slug="forged-heavy-duty-crankshaft",
            category_id=cat_closed.id if cat_closed else None,
            short_description="Precision closed-die forged alloy crankshaft for multi-cylinder heavy commercial diesel engines.",
            detailed_description="Manufactured from vacuum-degassed 42CrMo4 / AISI 4340 alloy steel on our 4000 MT hydraulic forging press. Features continuous fiber grain flow around pin and journal webs for maximum torsional fatigue life. Induction hardened journals achieve 52-58 HRC.",
            applications="Heavy commercial vehicles, locomotive diesel engines, marine propulsion auxiliary units, stationary power compressors.",
            material="AISI 4340 / 42CrMo4 / EN24 Alloy Steel",
            weight_range="25 kg to 140 kg",
            dimensions="Length 600 mm to 1,450 mm, Journal Dia 75 mm to 140 mm",
            manufacturing_process="Closed Die Press Forged & Induction Hardened",
            forging_capacity="Up to 4000 MT Press Line",
            heat_treatment="Quenched & Tempered + Pin/Journal Induction Hardened",
            machining="CNC rough turned and precision finish ground",
            surface_finish="Shot blasted, journal micro-polished to Ra 0.2 µm",
            testing="100% Wet Magnetic Particle Inspection & Phased Array UT",
            technical_specifications="Torsional fatigue strength >450 MPa. Web deflection under dynamic load <0.015 mm.",
            featured_image="/static/images/product_crankshaft.webp",
            downloads="/uploads/general/crankshaft_spec_sheet.pdf",
            meta_title="Forged Heavy-Duty Crankshafts | AISI 4340 Closed Die Forging",
            meta_description="Heavy-duty forged crankshafts for commercial automotive and locomotive engines. Fully balanced and induction hardened.",
            status="published",
            display_order=1,
        )
        if cap_closed: p1.capabilities.append(cap_closed)
        if cap_heat: p1.capabilities.append(cap_heat)
        if cap_machining: p1.capabilities.append(cap_machining)
        if ind_auto: p1.industries.append(ind_auto)
        if ind_rail: p1.industries.append(ind_rail)
        if mat_alloy: p1.materials.append(mat_alloy)
        if eq_press: p1.equipment.append(eq_press)

        # Specifications for p1
        p1.specifications = [
            ProductSpecification(name="Weight", value="85", unit="kg", display_order=1),
            ProductSpecification(name="Overall Length", value="980", unit="mm", display_order=2),
            ProductSpecification(name="Main Journal Dia", value="95", unit="mm", display_order=3),
            ProductSpecification(name="Pin Journal Dia", value="80", unit="mm", display_order=4),
            ProductSpecification(name="Forging Press Capacity", value="4000", unit="MT", display_order=5),
            ProductSpecification(name="Hardness", value="55", unit="HRC", display_order=6),
        ]

        # Product 2: Seamless Rolled Gear Ring
        p2 = Product(
            name="Seamless Rolled Slewing Gear Ring",
            slug="seamless-rolled-slewing-gear-ring",
            category_id=cat_rings.id if cat_rings else None,
            short_description="High-strength seamless rolled ring blank for wind turbine pitch bearings and heavy excavator slewing drives.",
            detailed_description="Formed using radial-axial CNC ring rolling technology that eliminates circumferential weld seams and produces unbroken grain flow in the tangential hoop direction. Provides superior resistance to shock loads and catastrophic tooth shearing.",
            applications="Wind turbine slewing bearings, mobile crane turntables, radar pedestals, marine winch gears.",
            material="42CrMo4 / AISI 4140 Normalized & Tempered",
            weight_range="75 kg to 1,200 kg",
            dimensions="Outer Diameter 600 mm to 2,800 mm, Face Width up to 350 mm",
            manufacturing_process="CNC Radial-Axial Seamless Ring Rolling",
            forging_capacity="Radial 250 MT / Axial 200 MT",
            heat_treatment="Normalizing, Polymer Quenching & Tempering (280-320 HB)",
            machining="Proof machined or finish CNC turned with gear teeth hobbed",
            surface_finish="Machined finish Ra 1.6 µm, anti-corrosive oil protected",
            testing="100% Volumetric Ultrasonic Examination (ASTM A388) & MPI",
            technical_specifications="Tensile strength 850-1000 MPa, Charpy V-notch impact >40 J at -20°C.",
            featured_image="/static/images/product_gear_ring.webp",
            downloads="/uploads/general/slewing_ring_spec.pdf",
            meta_title="Seamless Rolled Slewing Rings | Wind Turbine & Crane Gears",
            meta_description="Seamless rolled rings up to 2800mm OD for slewing bearings and gear blanks. Manufactured to EN 10222-2 standards.",
            status="published",
            display_order=2,
        )
        if cap_rings: p2.capabilities.append(cap_rings)
        if cap_heat: p2.capabilities.append(cap_heat)
        if ind_power: p2.industries.append(ind_power)
        if ind_heavy: p2.industries.append(ind_heavy)
        if mat_alloy: p2.materials.append(mat_alloy)

        p2.specifications = [
            ProductSpecification(name="Outer Diameter", value="1450", unit="mm", display_order=1),
            ProductSpecification(name="Inner Diameter", value="1220", unit="mm", display_order=2),
            ProductSpecification(name="Face Width", value="180", unit="mm", display_order=3),
            ProductSpecification(name="Finished Weight", value="380", unit="kg", display_order=4),
            ProductSpecification(name="Tensile Strength", value="920", unit="MPa", display_order=5),
        ]

        # Product 3: High-Pressure Forged Valve Body
        p3 = Product(
            name="High-Pressure Forged Valve Body",
            slug="high-pressure-forged-valve-body",
            category_id=cat_closed.id if cat_closed else None,
            short_description="Monolithic closed-die forged valve body for ANSI Class 1500/2500 oilfield subsea service.",
            detailed_description="Engineered for severe high-pressure, sour-gas (NACE MR0175 / ISO 15156) environments. Closed-die forging prevents internal porosity and weeping defects inherent to cast valve bodies, providing 100% pressure containment up to 15,000 PSI.",
            applications="Subsea Christmas trees, choke & kill manifolds, high-pressure steam isolation, chemical offshore platforms.",
            material="ASTM A182 F316L Stainless Steel / F22 Alloy Steel",
            weight_range="15 kg to 260 kg",
            dimensions="Bore size 2 inch to 12 inch (DN 50 to DN 300)",
            manufacturing_process="Closed Die Hydraulic Press Forged",
            forging_capacity="4000 MT Hydraulic Line",
            heat_treatment="Solution Annealed (F316L) / Normalized & Tempered (F22)",
            machining="CNC rough machined flanges and valve cavity",
            surface_finish="Pickled & Passivated (SS) / Phosphate Coated (Alloy)",
            testing="Liquid Penetrant Testing, Hydrostatic Pressure Testing to 1.5x rating",
            technical_specifications="Zero leakage containment tested to API Spec 6A PR2 Level.",
            featured_image="/static/images/product_valve_body.webp",
            downloads="/uploads/general/valve_body_spec.pdf",
            meta_title="High Pressure Forged Valve Bodies | API 6A & NACE MR0175",
            meta_description="Closed die forged valve bodies in stainless steel and F22 alloy for oil & gas subsea and high pressure flowline applications.",
            status="published",
            display_order=3,
        )
        if cap_closed: p3.capabilities.append(cap_closed)
        if ind_oil: p3.industries.append(ind_oil)
        if mat_stainless: p3.materials.append(mat_stainless)

        p3.specifications = [
            ProductSpecification(name="Pressure Rating", value="2500", unit="Class", display_order=1),
            ProductSpecification(name="Nominal Bore", value="150", unit="mm", display_order=2),
            ProductSpecification(name="Wall Thickness", value="38", unit="mm", display_order=3),
            ProductSpecification(name="Piece Weight", value="115", unit="kg", display_order=4),
            ProductSpecification(name="Test Pressure", value="375", unit="bar", display_order=5),
        ]

        # Product 4: Open Die Forged Turbine Rotor Shaft
        p4 = Product(
            name="Open Die Forged Turbine Rotor Shaft",
            slug="open-die-forged-turbine-rotor-shaft",
            category_id=cat_open.id if cat_open else None,
            short_description="Multi-stepped forged rotor shaft for hydroelectric turbines and thermal steam generators.",
            detailed_description="Custom open die forged under multi-ram cogging presses to guarantee fine axial grain orientation throughout the entire cross-section. Ultrasonic testing guarantees complete absence of center burst or shrinkage porosity.",
            applications="Hydroelectric Pelton and Francis turbines, steam turbo-generators, large marine propeller shafts.",
            material="26NiCrMoV14-5 / ASTM A470 Class 6 Alloy Steel",
            weight_range="500 kg to 8,500 kg",
            dimensions="Length up to 5,500 mm, Maximum Barrel Dia 850 mm",
            manufacturing_process="Open Die Free Forging with Multi-Stage Cogging",
            forging_capacity="Up to 15 MT Piece Weight",
            heat_treatment="Stress Relieved, Normalized, Liquid Quenched & Precision Tempered",
            machining="CNC rough turned with center hole trepanned for internal inspection",
            surface_finish="Proof machined Ra 3.2 µm with protective preservation wrapping",
            testing="100% Volumetric Ultrasonic Examination (ASTM A388) & Bore Inspection",
            technical_specifications="Yield strength >700 MPa, FATT50 < -20°C transition temperature.",
            featured_image="/static/images/product_turbine_shaft.webp",
            downloads="/uploads/general/turbine_shaft_catalog.pdf",
            meta_title="Open Die Forged Turbine Rotor Shafts | Power Generation",
            meta_description="Heavy open-die forged turbine shafts up to 8.5 MT. Multi-stepped rotor shafts engineered for power generation turbines.",
            status="published",
            display_order=4,
        )
        if cap_open: p4.capabilities.append(cap_open)
        if cap_test: p4.capabilities.append(cap_test)
        if ind_power: p4.industries.append(ind_power)
        if ind_heavy: p4.industries.append(ind_heavy)
        if mat_alloy: p4.materials.append(mat_alloy)

        p4.specifications = [
            ProductSpecification(name="Finished Length", value="4200", unit="mm", display_order=1),
            ProductSpecification(name="Max Barrel Dia", value="680", unit="mm", display_order=2),
            ProductSpecification(name="Weight", value="3450", unit="kg", display_order=3),
            ProductSpecification(name="Forging Press Capacity", value="4000", unit="MT", display_order=4),
            ProductSpecification(name="Impact Energy", value="65", unit="J", display_order=5),
        ]

        # Product 5: Precision Machined Planetary Sun Gear
        p5 = Product(
            name="Precision Machined Planetary Sun Gear",
            slug="precision-machined-planetary-sun-gear",
            category_id=cat_machined.id if cat_machined else None,
            short_description="Finished CNC ground sun gear with spline shaft for wind turbine and industrial reduction gearboxes.",
            detailed_description="Forged from carburizing grade 18CrNiMo7-6 steel, precision rough turned, gear shaped, vacuum carburized, and finish profile ground on CNC gear grinding machines to DIN 3962 Quality Grade 5.",
            applications="Wind turbine planetary gearboxes, heavy mining excavators, automated gantry drive transmissions.",
            material="18CrNiMo7-6 / AISI 8620 Alloy Steel",
            weight_range="8 kg to 95 kg",
            dimensions="Pitch Dia 150 mm to 450 mm, Module 4 to 12",
            manufacturing_process="Forged Blank -> CNC Turn -> Gear Hob -> Carburize -> Gear Grind",
            forging_capacity="2500 MT Mechanical Press Line",
            heat_treatment="Case Hardened (Carburized) 58-62 HRC, Case Depth 1.2-1.8 mm",
            machining="Finished gear tooth profile ground to DIN Class 5 / AGMA 12",
            surface_finish="Tooth flanks Ra 0.4 µm, root radius micro-shot peened",
            testing="Klingelnberg CNC Gear Analyzer Inspection & 100% MPI",
            technical_specifications="High contact fatigue endurance limit >1500 MPa. Low transmission error for silent operation.",
            featured_image="/static/images/product_sun_gear.webp",
            downloads="/uploads/general/gear_specification.pdf",
            meta_title="Precision Planetary Gears | CNC Ground Forged Gears",
            meta_description="Finish machined and ground planetary gears for wind and heavy industrial gearboxes. Certified to DIN 3962 Grade 5.",
            status="published",
            display_order=5,
        )
        if cap_machining: p5.capabilities.append(cap_machining)
        if cap_heat: p5.capabilities.append(cap_heat)
        if ind_heavy: p5.industries.append(ind_heavy)
        if ind_power: p5.industries.append(ind_power)
        if mat_alloy: p5.materials.append(mat_alloy)
        if eq_lathe: p5.equipment.append(eq_lathe)

        p5.specifications = [
            ProductSpecification(name="Pitch Diameter", value="280", unit="mm", display_order=1),
            ProductSpecification(name="Tooth Module", value="8", unit="mm", display_order=2),
            ProductSpecification(name="Number of Teeth", value="35", unit="", display_order=3),
            ProductSpecification(name="Weight", value="42", unit="kg", display_order=4),
            ProductSpecification(name="Case Hardness", value="60", unit="HRC", display_order=5),
        ]

        # Link related products
        p1.related_products = [p2, p5]
        p2.related_products = [p1, p4]
        p3.related_products = [p1, p4]
        p4.related_products = [p2, p3]
        p5.related_products = [p1, p2]

        for p in [p1, p2, p3, p4, p5]:
            if not db.query(Product).filter(Product.slug == p.slug).first():
                db.add(p)
        db.commit()
        stats["products"] = db.query(Product).count()
        logger.info("Seeded products with full specifications, relationships, and technical details.")
    else:
        stats["products"] = db.query(Product).count()

    # Seed Phase 4 Modules
    seed_phase_4_data(db, stats)

    return stats


def seed_phase_4_data(db: Session, stats: dict) -> None:
    """
    Seeds Phase 4 content: Blog posts, Case studies, reusable FAQs,
    Downloadable technical resources, dynamic site settings, and social links.
    """
    # 1. Site Settings & Social Links
    settings_service.seed_defaults(db)

    # 2. Blog Posts
    now = datetime.now(timezone.utc)
    blog_seed = [
        BlogPost(
            title="Advancements in High-Precision Closed Die Forging for Automotive Powertrains",
            slug="closed-die-forging-automotive-powertrains",
            featured_image="/static/images/closed_die_forging.webp",
            author="Metallurgical Engineering Lead",
            category=BlogCategory.FORGING_TECHNOLOGY.value,
            excerpt="How modern automated forging presses with optical thermal feedback and multi-cavity dies produce net-shape connecting rods and crankshafts with zero porosity.",
            content="""<p>In high-performance automotive powertrains, structural endurance and torsional fatigue resistance are non-negotiable. Modern automotive applications require components that can sustain millions of cyclic load reversals without mechanical failure.</p>
<h3>Grain Alignment and Continuous Grain Flow</h3>
<p>Unlike casting or machining from rolled bar stock, closed-die impression forging forces the metal to flow along the component contour. This unbroken grain orientation dramatically increases fatigue life, impact toughness, and ductility under fluctuating mechanical loads.</p>
<h3>Statistical Process Control & Thermal Monitoring</h3>
<p>Our automated press lines monitor billet induction temperature at ±10°C tolerance before entering the preforming impression. Laser scanning verifies die cavity filling dynamically, ensuring zero cold-shut defects and tight geometric repeatability conforming to EN 10243-1 Grade F.</p>""",
            tags="Forging,Automotive,Closed Die,Engineering",
            publish_date=now,
            status=BlogPostStatus.PUBLISHED.value,
            seo_title="Automotive Powertrain Closed Die Forging Innovations",
            meta_description="Explore precision closed-die forging technologies for automotive crankshafts and connecting rods. Grain flow optimization and zero-porosity metallurgy.",
            reading_time_minutes=6,
        ),
        BlogPost(
            title="Grain Flow Optimization vs Traditional Casting in High-Stress Components",
            slug="grain-flow-optimization-vs-casting",
            featured_image="/static/images/open_die_forging.webp",
            author="Chief Metallurgist",
            category=BlogCategory.ENGINEERING.value,
            excerpt="A metallurgical comparison of grain boundary continuity in forged steel versus dendritic shrinkage porosity in castings subjected to severe fatigue.",
            content="""<p>When selecting manufacturing methods for mission-critical parts such as turbine discs, steering knuckles, and high-pressure valve bodies, engineers frequently evaluate forgings against castings.</p>
<h3>The Metallurgical Advantage of Forging</h3>
<p>Forging refines the coarse as-cast dendritic microstructure through substantial plastic deformation (upsetting and cogging). This breaks up inclusions, closes internal micro-voids, and reorients crystal structures along the principal stress directions.</p>
<h3>Tensile and Charpy V-Notch Impact Superiority</h3>
<p>Laboratory testing confirms that forged alloy steels consistently deliver 25% to 35% higher yield strength and more than double the Charpy impact energy at sub-zero temperatures (-40°C) compared to cast equivalents of identical nominal chemistry.</p>""",
            tags="Metallurgy,Grain Flow,Casting vs Forging,Engineering",
            publish_date=now,
            status=BlogPostStatus.PUBLISHED.value,
            seo_title="Forging vs Casting: Grain Flow and Fatigue Comparison",
            meta_description="Comprehensive metallurgical evaluation of continuous grain flow in forgings compared to cast components under extreme cyclic stress.",
            reading_time_minutes=7,
        ),
        BlogPost(
            title="Global Supply Chain Shifts in Industrial Heavy Forgings",
            slug="global-supply-chain-heavy-forgings",
            featured_image="/static/images/facilities_heavy_press.webp",
            author="Supply Chain & Strategy Director",
            category=BlogCategory.INDUSTRY_INSIGHTS.value,
            excerpt="Key dynamics shaping global forging procurement: near-shoring, raw material hedging, carbon footprint reduction, and dual-sourcing strategies.",
            content="""<p>Global industrial supply chains are prioritizing reliability, regional resilience, and verifiable ESG certifications. Original equipment manufacturers (OEMs) across Europe and North America are actively partnering with integrated forging and machining specialists.</p>
<h3>Single-Source Turnkey Manufacturing</h3>
<p>OEMs increasingly seek Tier-1 suppliers capable of managing the full value stream: billet sourcing, open-die and closed-die forging, heat treatment, rough turning, finish CNC grinding, and full NDT certification under one roof. This minimizes transit bottlenecks and reduces administrative overhead.</p>""",
            tags="Supply Chain,Industrial,Strategy,Procurement",
            publish_date=now,
            status=BlogPostStatus.PUBLISHED.value,
            seo_title="Global Trends in Heavy Forging Supply Chains | 2026 Analysis",
            meta_description="Analysis of international procurement strategies in heavy open-die and closed-die forgings. Managing lead times and certified quality.",
            reading_time_minutes=5,
        ),
        BlogPost(
            title="Metallurgical Purity and Ultrasonic Testing in Vacuum Degassed Steels",
            slug="ultrasonic-testing-vacuum-degassed-steels",
            featured_image="/static/images/facility_lab.webp",
            author="Quality Assurance Director",
            category=BlogCategory.QUALITY.value,
            excerpt="Why secondary metallurgical refining and immersion ultrasonic scanning per ASTM A388 are mandatory for critical aerospace and energy forgings.",
            content="""<p>Internal soundness is the cornerstone of high-integrity forging. Hydrogen embrittlement, non-metallic inclusion clusters, and macro-segregation can lead to catastrophic fracture under high hydrostatic or cyclic loads.</p>
<h3>Vacuum Degassing & Ladle Refining</h3>
<p>All forging ingots and billets are procured with vacuum degassing (VD/VOD), reducing dissolved hydrogen to under 1.5 ppm and total oxygen to under 15 ppm. This guarantees extreme cleanliness conforming to ASTM E45 Method A.</p>
<h3>100% Volume Ultrasonic Examination</h3>
<p>Our ASNT Level II and Level III certified inspectors conduct complete volumetric ultrasonic testing in accordance with ASTM A388, EN 10228-3, and API 6A requirements, detecting internal discontinuities smaller than 1.5 mm flat-bottom hole equivalents.</p>""",
            tags="Quality,Ultrasonic Testing,NDT,ASTM,Metallurgy",
            publish_date=now,
            status=BlogPostStatus.PUBLISHED.value,
            seo_title="Ultrasonic Testing Standards in Forged Steel | ASTM A388",
            meta_description="Understanding vacuum degassed steel refining and 100% volumetric ultrasonic inspection standards for critical heavy forgings.",
            reading_time_minutes=8,
        ),
        BlogPost(
            title="Expanding Plant Capacity: Commissioning of New 6,300 MT Press Line",
            slug="plant-expansion-6300mt-press-line",
            featured_image="/static/images/equipment_hammer.webp",
            author="Corporate Communications",
            category=BlogCategory.COMPANY_NEWS.value,
            excerpt="New automated 6,300 Metric Ton hydraulic forging line enhances single-piece closed-die forging capacity up to 180 kg with robotic transfer.",
            content="""<p>We are proud to announce the successful installation and commissioning of our new 6,300 MT heavy-duty forging press line at our main plant. This strategic expansion increases our annual closed-die forging capacity by 18,000 metric tons.</p>
<h3>Robotic Material Handling & Energy Efficiency</h3>
<p>The press line is integrated with heavy payload robotic transfer systems and energy-efficient regenerative servo drives that reduce electrical power consumption per ton of steel forged by 22%.</p>""",
            tags="Company News,Expansion,Press Line,Manufacturing",
            publish_date=now,
            status=BlogPostStatus.PUBLISHED.value,
            seo_title="New 6,300 MT Heavy Forging Press Commissioned",
            meta_description="Plant capacity expansion: 6,300 MT automated forging press commissioned for heavy closed-die industrial components.",
            reading_time_minutes=4,
        ),
        BlogPost(
            title="Near-Net Shape Ring Rolling: Reducing Raw Material Scrap by 35%",
            slug="near-net-shape-ring-rolling-scrap-reduction",
            featured_image="/static/images/ring_rolling.webp",
            author="Senior Manufacturing Engineer",
            category=BlogCategory.MANUFACTURING.value,
            excerpt="How CNC radial-axial ring rolling minimizes machining allowances and saves valuable nickel and titanium alloys.",
            content="""<p>In aerospace flanges, slewing rings, and high-pressure pipeline connections, machining massive rings from solid plate or hollow bar generates enormous metal waste. Radial-axial ring rolling provides the superior economic and mechanical solution.</p>
<h3>Tangential Grain Orientation</h3>
<p>Continuous circumferential deformation creates tangential grain alignment that maximizes hoop stress containment while keeping raw material input 30% to 40% lower than flame-cut forged plate rings.</p>""",
            tags="Ring Rolling,Manufacturing,Near Net Shape,Sustainability",
            publish_date=now,
            status=BlogPostStatus.PUBLISHED.value,
            seo_title="Near-Net Shape Ring Rolling Technology | Material Efficiency",
            meta_description="Learn how CNC seamless ring rolling optimizes grain flow and slashes machining scrap on high-alloy rings up to 3,500 mm OD.",
            reading_time_minutes=6,
        ),
        BlogPost(
            title="Engineering Case Study: Heavy Duty Diesel Engine Crankshaft Redesign",
            slug="case-study-diesel-crankshaft-redesign",
            featured_image="/static/images/product_crankshaft.webp",
            author="R&D Engineering Group",
            category=BlogCategory.CASE_STUDIES.value,
            excerpt="Deep dive into a successful weight reduction and fatigue life enhancement project for a 12-liter commercial vehicle engine program.",
            content="""<p>A major commercial vehicle manufacturer approached our engineering team to reduce reciprocating mass in their flagship 12-liter inline-6 diesel engine while extending bearing pin fatigue life by 40%.</p>
<h3>Finite Element Forging Simulation & Grain Optimization</h3>
<p>Using DEFORM-3D finite element simulation, our tooling designers optimized the pre-forming blocker dies, redistributing mass to web fillets and counterweights without increasing total forging billet weight.</p>""",
            tags="Case Studies,Crankshaft,Automotive,R&D",
            publish_date=now,
            status=BlogPostStatus.PUBLISHED.value,
            seo_title="Diesel Crankshaft Forging Engineering Case Study",
            meta_description="Technical case study detailing how finite element forging simulation and micro-alloyed steel achieved 18% weight reduction in diesel crankshafts.",
            reading_time_minutes=7,
        ),
    ]
    for b in blog_seed:
        if not db.query(BlogPost).filter(BlogPost.slug == b.slug).first():
            db.add(b)
    db.commit()
    stats["blog_posts"] = db.query(BlogPost).count()

    # 3. Case Studies
    cs_seed = [
        CaseStudy(
            title="Heavy-Duty Diesel Crankshaft Weight & Fatigue Optimization",
            slug="heavy-duty-diesel-crankshaft-optimization",
            featured_image="/static/images/product_crankshaft.webp",
            client_industry="Commercial Vehicle & Heavy Truck OEM",
            client_challenge="A global heavy truck engine manufacturer required an 18% reduction in crankshaft mass while simultaneously improving torsional fatigue endurance by 30% to meet stringent Euro VI / EPA emissions mandates.",
            engineering_approach="Our technical team executed 3D computer finite element forging simulations to optimize billet pre-forming, eliminate flash waste, and redirect continuous grain flow through crankpin fillets. We switched from standard 42CrMo4 to micro-alloyed 38MnSiVS5 steel with controlled cooling to eliminate secondary quench cracking.",
            material="38MnSiVS5 Micro-alloyed Forging Steel (EN 10267)",
            forging_process="Automated 6,300 MT mechanical forging press with closed impression dies and optical laser pyrometer temperature tracking.",
            machining="CNC multi-axis pin milling, deep-hole oil gallery gun drilling, induction journal hardening (54-58 HRC), and superfinishing to Ra 0.15 µm.",
            quality_requirements="100% wet magnetic particle inspection (MPI), ultrasonic flaw detection per EN 10228-3 Class 3, and optical coordinate measuring machine (CMM) dimensional verification.",
            result="Achieved 18.4% reduction in rotating mass, zero internal porosity defects across 25,000 serial units, and an estimated 4.2% reduction in engine fuel consumption during dynamometer testing.",
            gallery_json=json.dumps([
                "/static/images/product_crankshaft.webp",
                "/static/images/closed_die_forging.webp",
                "/static/images/equipment_lathe.webp",
            ]),
            downloads_json=json.dumps([
                {"title": "Crankshaft Forging Specification Sheet", "url": "/uploads/downloads/crankshaft_drawing_template.pdf"},
                {"title": "Material Test & Metallurgical Report", "url": "/uploads/downloads/forging_design_guide.pdf"}
            ]),
            cta_text="Discuss Your Powertrain Forging Challenge",
            cta_link="/request-a-quote?product=Crankshaft&material=38MnSiVS5",
            seo_title="Heavy Truck Diesel Crankshaft Forging Case Study",
            meta_description="Read how our engineering team redesigned a 12L diesel engine crankshaft, achieving 18% weight reduction and superior fatigue life.",
            status="published",
            display_order=1,
        ),
        CaseStudy(
            title="Seamless Forged Rings for 12 MW Offshore Wind Turbine Slewing Bearings",
            slug="seamless-forged-ring-offshore-wind",
            featured_image="/static/images/product_rolled_ring.webp",
            client_industry="Offshore Renewable Energy & Wind Turbines",
            client_challenge="Client needed ultra-large seamless rolled rings (OD 3,200 mm) with zero weld seams, capable of enduring extreme cyclic bending moments in harsh marine North Sea environments for 25-year service life.",
            engineering_approach="Utilized vacuum degassed 42CrMo4 alloy steel ingots with electroslag remelting (ESR). Executed precision core piercing followed by CNC radial-axial ring rolling to establish tangential grain alignment throughout the full circumference.",
            material="42CrMo4+QT / AISI 4140 Quenched & Tempered Steel",
            forging_process="Radial-axial CNC ring rolling machine with 400 MT radial and 320 MT axial rolling force.",
            machining="Vertical CNC boring and turning to precision raceway tolerances within ±0.08 mm.",
            quality_requirements="Sub-zero Charpy V-notch impact testing at -40°C (>42 Joules), 100% volumetric ultrasonic testing per EN 10228-3 Class 4.",
            result="Delivered 180 ring sets with 100% ultrasonic compliance, zero grain boundary embrittlement, and flawless installation in offshore wind platforms.",
            gallery_json=json.dumps([
                "/static/images/product_rolled_ring.webp",
                "/static/images/ring_rolling.webp",
                "/static/images/facilities_heavy_press.webp",
            ]),
            downloads_json=json.dumps([
                {"title": "Seamless Rolled Ring Technical Specs", "url": "/uploads/downloads/forging_corporate_brochure.pdf"}
            ]),
            cta_text="Request a Ring Rolling Engineering Review",
            cta_link="/request-a-quote?product=Rolled+Ring&material=42CrMo4",
            seo_title="Offshore Wind Slewing Ring Forging Case Study",
            meta_description="Case study: Seamless forged rings up to 3,200 mm OD for 12 MW offshore wind turbines. Sub-zero impact toughness at -40°C.",
            status="published",
            display_order=2,
        ),
        CaseStudy(
            title="Subsea Valve Body Forging in Super Duplex Stainless Steel (UNS S32750)",
            slug="subsea-valve-body-duplex-forging",
            featured_image="/static/images/product_hollow_forging.webp",
            client_industry="Subsea Oil & Gas / Deepwater Extraction",
            client_challenge="Deepwater exploration equipment operating at 3,000 meters water depth subjected to 15,000 PSI hydrostatic pressure and sour crude oil containing high concentrations of H2S and chlorides.",
            engineering_approach="Engineered a near-net shape closed-die forging process in Super Duplex Stainless Steel (2507 / UNS S32750). Rigorous solution annealing at 1,120°C followed by high-velocity water quenching prevented intermetallic sigma phase precipitation.",
            material="Super Duplex Stainless Steel UNS S32750 / EN 1.4410",
            forging_process="Hydraulic press forging with preheated ceramic-coated dies to prevent surface chilling.",
            machining="Rough and finish 5-axis CNC machining of flange faces and internal seal cavities.",
            quality_requirements="ASTM G48 Method A ferric chloride pitting corrosion testing, microstructural ferrite/austenite ratio analysis (45-55%), NACE MR0175 / ISO 15156 compliance.",
            result="100% pass rate in critical pitting temperature tests (>50°C), zero sigma phase detection under scanning electron microscopy, and complete API 6A PR2 certification.",
            gallery_json=json.dumps([
                "/static/images/product_hollow_forging.webp",
                "/static/images/facility_lab.webp",
            ]),
            downloads_json=json.dumps([
                {"title": "Super Duplex Metallurgy Report", "url": "/uploads/downloads/forging_design_guide.pdf"}
            ]),
            cta_text="Consult Subsea Metallurgy Specialists",
            cta_link="/request-a-quote?product=Valve+Body&material=Super+Duplex",
            seo_title="Subsea Valve Body Super Duplex Forging Case Study",
            meta_description="Engineering case study on forging high-pressure subsea valve bodies in Super Duplex UNS S32750 per API 6A and NACE MR0175.",
            status="published",
            display_order=3,
        ),
    ]
    for cs in cs_seed:
        if not db.query(CaseStudy).filter(CaseStudy.slug == cs.slug).first():
            db.add(cs)
    db.commit()
    stats["case_studies"] = db.query(CaseStudy).count()

    # 4. Reusable FAQs
    faqs_seed = [
        FAQ(
            question="What materials and steel grades can your forging facility manufacture?",
            answer="We forge a wide spectrum of carbon steels (AISI 1020 to 1045, EN 8/EN 9), alloy steels (42CrMo4, 18CrNiMo7-6, 16MnCr5, 20MnCr5), micro-alloyed steels (38MnSiVS5), austenitic and martensitic stainless steels (SS304, SS316L, 17-4PH), and high-integrity Super Duplex stainless steels (UNS S32750 / 2507). All material is sourced exclusively with EN 10204 3.1 certification and vacuum degassing.",
            category="Quality & Metallurgy",
            related_entity="homepage",
            display_order=1,
            is_active=True,
        ),
        FAQ(
            question="What is your maximum piece weight and dimensional forging capacity?",
            answer="Our open die forging presses handle single-piece forgings up to 15 Metric Tons with diameters up to 1,200 mm and lengths up to 6,000 mm. For closed-die components, our press and hammer lines produce components from 0.5 kg up to 180 kg. Our CNC ring rolling facility produces seamless rings up to 3,500 mm outer diameter.",
            category="Technical Specifications",
            related_entity="homepage",
            display_order=2,
            is_active=True,
        ),
        FAQ(
            question="Do you provide fully finished CNC machined components ready for assembly?",
            answer="Yes. Our in-house machine shop features over 45 CNC turning centers, vertical and horizontal machining centers (VMC/HMC), cylindrical grinders, and gear shapers. We deliver forgings as rough turned, proof machined, or fully finish ground with microns-level tolerances.",
            category="Machining & Tolerances",
            related_entity="homepage",
            display_order=3,
            is_active=True,
        ),
        FAQ(
            question="What quality certifications and non-destructive testing (NDT) capabilities do you maintain?",
            answer="Our plants are certified to ISO 9001:2015, IATF 16949 (Automotive), AS9100D (Aerospace), and PED 2014/68/EU (Pressure Equipment). In-house testing includes 100% Ultrasonic Testing (UT), Magnetic Particle Inspection (MPI), Liquid Penetrant Testing (LPT), Optical Spectrometry, and Charpy impact testing down to -40°C.",
            category="Quality & Metallurgy",
            related_entity="quality",
            display_order=4,
            is_active=True,
        ),
        FAQ(
            question="What is the typical lead time for new tooling and first-article prototype sampling?",
            answer="New tooling design and 3D simulation typically requires 2 to 3 weeks. Tool manufacturing and first-article pilot batch forging with full dimensional inspection (PPAP Level 3) is completed within 4 to 6 weeks from tooling sign-off.",
            category="Tooling & Lead Times",
            related_entity="products",
            display_order=5,
            is_active=True,
        ),
        FAQ(
            question="How can I submit drawings to get a formal quotation?",
            answer="You can upload 2D drawings (PDF, DWG, DXF) or 3D models (STEP, STP, IGES) directly via our /request-a-quote portal or email rfq@forgingcms.com. Our engineering estimation department provides formal proposals with manufacturing feasibility notes within 48 business hours.",
            category="Ordering & Logistics",
            related_entity="contact",
            display_order=6,
            is_active=True,
        ),
    ]
    for f in faqs_seed:
        if not db.query(FAQ).filter(FAQ.question == f.question).first():
            db.add(f)
    db.commit()
    stats["faqs"] = db.query(FAQ).count()

    # 5. Downloads
    downloads_seed = [
        DownloadResource(
            title="Industrial Forging Capabilities & Infrastructure Corporate Brochure",
            description="Comprehensive overview of open-die presses, closed-die lines, CNC ring rolling, and testing laboratories.",
            file_path="/uploads/downloads/forging_corporate_brochure.pdf",
            file_type="PDF",
            file_size_bytes=4250000,
            category=DownloadCategory.BROCHURE.value,
            visibility=DownloadVisibility.PUBLIC.value,
            display_order=1,
            is_active=True,
        ),
        DownloadResource(
            title="Design Engineers Guide to Forging Tolerances & Metallurgy",
            description="Technical design manual detailing machining allowances, draft angles, fillet radii, and steel grade cross-reference tables.",
            file_path="/uploads/downloads/forging_design_guide.pdf",
            file_type="PDF",
            file_size_bytes=6800000,
            category=DownloadCategory.TECHNICAL_DOCUMENT.value,
            visibility=DownloadVisibility.PUBLIC.value,
            display_order=2,
            is_active=True,
        ),
        DownloadResource(
            title="Precision Forged Components Full Product Catalog (2026 Edition)",
            description="Complete product range catalog: crankshafts, seamless rolled rings, hollow shafts, bevel gears, and valve bodies.",
            file_path="/uploads/downloads/product_catalog_2026.pdf",
            file_type="PDF",
            file_size_bytes=8900000,
            category=DownloadCategory.CATALOG.value,
            visibility=DownloadVisibility.PUBLIC.value,
            display_order=3,
            is_active=True,
        ),
        DownloadResource(
            title="ISO 9001:2015, IATF 16949 & PED Quality Certificates Portfolio",
            description="Official accreditation certificates from TÜV Rheinland and Lloyd's Register for automotive and pressure equipment.",
            file_path="/uploads/downloads/iso_iatf_certificates.pdf",
            file_type="PDF",
            file_size_bytes=2100000,
            category=DownloadCategory.CERTIFICATE.value,
            visibility=DownloadVisibility.PUBLIC.value,
            display_order=4,
            is_active=True,
        ),
        DownloadResource(
            title="Crankshaft 2D & 3D Engineering Drawing Templates (Sample Spec)",
            description="Dimensional drawing specification template and GD&T tolerance standards for closed-die forged crankshafts.",
            file_path="/uploads/downloads/crankshaft_drawing_template.pdf",
            file_type="PDF",
            file_size_bytes=3400000,
            category=DownloadCategory.PRODUCT_DRAWING.value,
            visibility=DownloadVisibility.PUBLIC.value,
            display_order=5,
            is_active=True,
        ),
    ]
    for d in downloads_seed:
        if not db.query(DownloadResource).filter(DownloadResource.title == d.title).first():
            db.add(d)
    db.commit()
    stats["downloads"] = db.query(DownloadResource).count()

    # 6. Dynamic CMS Pages & Menus counts
    from app.models.page import CMSPage
    from app.models.menu import MenuItem
    stats["cms_pages"] = db.query(CMSPage).count()
    stats["menu_items"] = db.query(MenuItem).count()

    logger.info(f"CMS database bootstrap complete: {stats}")
    return stats


