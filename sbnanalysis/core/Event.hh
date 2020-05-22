#ifndef __sbnanalysis_core_Event__
#define __sbnanalysis_core_Event__

/**
 * \file Event.hh
 *
 * The standard minimum output tree.
 *
 * This event structure is written out by every Processor subclass.
 *
 * Author: A. Mastbaum <mastbaum@uchicago.edu>, 2018/01/25
 */

#include <map>
#include <string>
#include <vector>
//#include <TTree.h>

#include "TVector3.h"

namespace event{
  // This helps us hide the rest of TVector3's fields from gen_proxy
  struct SRVector3D{
    SRVector3D(){}
    SRVector3D(double x, double y, double z) : fX(x), fY(y), fZ(z) {}
    SRVector3D(const TVector3& v) : fX(v.X()), fY(v.Y()), fZ(v.Z()) {}
    float fX, fY, fZ;
  };
}

#ifdef GEN_FLATRECORD_CONTEXT
#define TVector3 SRVector3D
#endif

#include "Experiment.hh"

namespace event {

static const int kUnfilled = -99999;  //!< Value for unfilled variables

/**
 * \class Metadata
 * \brief Event-level information
 */
class Metadata {
public:
  /** Constructor. */
  Metadata() : run(kUnfilled), subrun(kUnfilled), eventID(kUnfilled) {}

  /** Reset members to defaults. */
  void Init() {
    run = kUnfilled;
    subrun = kUnfilled;
    eventID = kUnfilled;
  }

  int run;      //!< Run ID
  int subrun;   //!< Subrun ID
  int eventID;  //!< Event ID
  int fileEntry; //!< Index of of file
};


/**
 * \class Neutrino
 * \brief Neutrino interaction information
 */
class Neutrino {
public:
  /** Constructor. */
  Neutrino()
    : isnc(false), iscc(false), initpdg(0), pdg(0), targetPDG(0),
      genie_intcode(0), bjorkenX(kUnfilled), inelasticityY(kUnfilled),
      Q2(kUnfilled), q0(kUnfilled),
      modq(kUnfilled), q0_lab(kUnfilled), modq_lab(kUnfilled),
      w(kUnfilled), t(kUnfilled), energy(kUnfilled),
      momentum(kUnfilled, kUnfilled, kUnfilled), parentPDG(0),
      parentDecayMode(0), parentDecayVtx(kUnfilled, kUnfilled, kUnfilled),
      baseline(kUnfilled) {}

  bool isnc;                //!< same as LArSoft "ccnc" - 0=CC, 1=NC
  bool iscc;                //!< CC (true) or NC/interference (false)
  int initpdg;              //!< Initial PDG code of probe neutrino
  int pdg;                  //!< PDG code of probe neutrino
  int targetPDG;            //!< PDG code of struck target
  int genie_intcode;        //!< Interaction mode (as for LArSoft MCNeutrino::Mode() )
  float bjorkenX;          //!< Bjorken x
  float inelasticityY;     //!< Inelasticity y
  float Q2;                //!< Q squared
  float q0;                //!< q0, struck nucleon rest frame
  float modq;              //!< |q|, struck nucleon rest frame
  float q0_lab;            //!< q0, lab frame
  float modq_lab;          //!< |q|, lab frame
  float w;                 //!< Hadronic invariant mass W
  float t;                 //!< Kinematic t
  float eccqe;             //!< CCQE energy
  float energy;            //!< Neutrino energy (GeV)
  TVector3 momentum;        //!< Neutrino three-momentum
  TVector3 position;        //!< Neutrino interaction position
  int parentPDG;            //!< Parent hadron/muon PDG
  int parentDecayMode;      //!< Parent hadron/muon decay mode
  TVector3 parentDecayVtx;  //!< Parent hadron/muon decay vertex
  float baseline;          //!< Distance from decay to interaction
};


/**
 * \class FinalStateParticle
 * \brief Final state particle information
 */
class FinalStateParticle {
public:
  /** Constructor. */
  FinalStateParticle()
    : pdg(kUnfilled), energy(kUnfilled),
      momentum(kUnfilled, kUnfilled, kUnfilled) {}

  /** GENIE status codes, see Framework/GHEP/GHepStatus.h for details */
  enum GenieStatus {
    kIStUndefined                = -1, 
    kIStInitialState             =  0,
    kIStStableFinalState         =  1,
    kIStIntermediateState        =  2,
    kIStDecayedState             =  3,
    kIStCorrelatedNucleon        = 10,
    kIStNucleonTarget            = 11,
    kIStDISPreFragmHadronicState = 12,
    kIStPreDecayResonantState    = 13,
    kIStHadronInTheNucleus       = 14,
    kIStFinalStateNuclearRemnant = 15,
    kIStNucleonClusterTarget     = 16
  };

  int pdg;  //!< PDG Code
  float energy;  //!< Energy
  TVector3 momentum;  //!< Three-momentum
  TVector3 start;  //!< Start position in detector coords [cm]
  TVector3 end;  //!< End position in detector coords (may be outside of AV) [cm]

  /**
   * Length of particle contained in the detector active volume [cm]
   * Set to -1 if no Detector is defined through the ProviderManager
   * Set to 0 for a particle that originates outside the detector active volume
   */
  float contained_length;

  float length; //!< Total length of the energy depositions [cm]
  bool is_primary; //!< Whether the process producing the particle was "primary"
  int status_code; //!< Status code returned by GENIE (see GenieStatus enum)
};


/**
 * \class Interaction
 * \brief All truth information associated with one neutrino interaction
 */
#ifndef GEN_FLATRECORD_CONTEXT
class Interaction {
public:
  Neutrino neutrino;  //!< The neutrino
  FinalStateParticle lepton;  //!< The primary final state lepton
  std::vector<FinalStateParticle> finalstate; //!< Other final state particles
  size_t nfinalstate;  //!< Size of finalstate

  /**
   * Event weights.
   *
   * This is a map from the weight calculator name to the list of weights
   * for all the sampled universes.
   */
  std::map<std::string, std::vector<float> > weights;

  size_t index;  //!< Index in the MCTruth
};
#endif

// This allows SRProxy to work around the map in the systs
struct SRPair{
  SRPair(const std::pair<std::string, std::vector<float>>& p) : first(p.first), second(p.second) {}
  std::string first;
  std::vector<float> second;
};

class SRInteraction
{
public:
  SRInteraction(){}
#ifndef GEN_FLATRECORD_CONTEXT
  SRInteraction(const Interaction& i)
    : neutrino(i.neutrino),
      lepton(i.lepton),
      finalstate(i.finalstate),
      nfinalstate(i.nfinalstate),
      weights(i.weights.begin(), i.weights.end()),
      index(i.index)
  {
  }
#endif

  Neutrino neutrino;
  FinalStateParticle lepton;
  std::vector<FinalStateParticle> finalstate;
  size_t nfinalstate;
  std::vector<SRPair> weights;
  size_t index;
};

/**
 * \class RecoInteraction
 * \brief Contains truth level information and additional fields for
 * selection-defined reconstruction information
 */
class RecoInteraction {
public:
  /** Default Constructor */
  RecoInteraction()
      : truth_index(-1), reco_energy(kUnfilled), weight(1) {}

  /** Fill in truth information -- other fields set as in default */
  explicit RecoInteraction(int tindex)
      : truth_index(tindex), reco_energy(kUnfilled), weight(1) {}

  /**
   * Index into the vector of truth interaction objects in the Event
   * (same as the index into MCTruth objects). Equal to -1 if there is
   * no corresponding truth interaction.
   */
  int truth_index;

  float reco_energy;  //!< Reconstructed neutrino energy [GeV]
  float weight;  //!< Selection-defined event weight
  size_t index;  //!< Index in the reco vector
};


/**
 * \class RecoEvent
 * \brief The reconstructed event data definition.
 *
 * An Event contains a single reconstructed neutrino with the corresponding
 * truth information for the best-matched true neutrino, if available.
 */
class RecoEvent {
public:
  auto GetTruth() {
    return truth.empty() ? NULL : &truth.at(0);
  }

  Metadata metadata;  //!< Event metadata
  RecoInteraction reco; //!< Reconstructed interaction
#ifndef GEN_FLATRECORD_CONTEXT
  std::vector<Interaction> truth; //!< Associated truth interaction
#else
  std::vector<SRInteraction> truth;
#endif
  Experiment experiment;  //!< Experiment identifier
};


/**
 * \class Event
 * \brief The standard event data definition.
 *
 * An Event contains all Monte Carlo events, with lists of all true
 * and reconstructed neutrinos.
 */
class Event {
public:
  Metadata metadata;  //!< Event metadata
  size_t ntruth;  //!< Size of truth
#ifndef GEN_FLATRECORD_CONTEXT
  std::vector<Interaction> truth; //!< All truth interactions
#else
  std::vector<SRInteraction> truth;
#endif
  size_t nreco;  //!< Size of reco
  std::vector<RecoInteraction> reco; //!< Reconstructed interactions
  Experiment experiment;  //!< Experiment identifier
};

}  // namespace event

#endif  // __sbnanalysis_core_Event__

