#ifndef __sbnanalysis_ana_SBNOsc_NumuRecoSelection__
#define __sbnanalysis_ana_SBNOsc_NumuRecoSelection__

/**
 * \file NumuRecoSelection.h
 *
 * SBN nue selection.
 *
 * Author:
 */

#include <iostream>
#include <array>
#include <vector>

#include "canvas/Utilities/InputTag.h"
#include "core/SelectionBase.hh"
#include "core/Event.hh"
#include "core/ProviderManager.hh"

#include "TDatabasePDG.h"
#include "TGraph.h"

#include "canvas/Persistency/Common/FindManyP.h"
#include "lardataobj/Simulation/GeneratedParticleInfo.h"
#include "nusimdata/SimulationBase/MCTruth.h"
#include "lardataobj/MCBase/MCTrack.h"
#include "lardataobj/RecoBase/Vertex.h"
#include "lardataobj/RecoBase/Track.h"
#include "lardataobj/RecoBase/Hit.h"
#include "larcorealg/Geometry/BoxBoundedGeo.h"

#include "LArReco/TrajectoryMCSFitter.h"
#include "LArReco/TrackMomentumCalculator.h"

#include "sbndcode/CRT/CRTProducts/CRTHit.hh"
#include "sbndcode/CRT/CRTProducts/CRTTrack.hh"

#include "sbndcode/CRT/CRTUtils/CRTT0MatchAlg.h"
#include "sbndcode/CRT/CRTUtils/CRTTrackMatchAlg.h"

#include "CosmicIDAlgs/ApaCrossCosmicIdAlg.h"
#include "CosmicIDAlgs/StoppingParticleCosmicIdAlg.h"
#include "OpHitFinder/opHitFinderSBND.hh"

class TH2D;
class TH1D;

namespace ana {
  namespace SBNOsc {

/**
 * \class NumuRecoSelection
 * \brief Electron neutrino event selection
 */
class NumuRecoSelection : public core::SelectionBase {
public:
  /** Constructor. */
  NumuRecoSelection();

  /**
   * Initialization.
   *
   * \param config A configuration, as a FHiCL ParameterSet object
   */
  void Initialize(fhicl::ParameterSet* config=NULL);

  /** Finalize and write objects to the output file. */
  void Finalize();

  /**
   * Process one event.
   *
   * \param ev A single event, as a gallery::Event
   * \param Reconstructed interactions
   * \return True to keep event
   */
  bool ProcessEvent(const gallery::Event& ev, const std::vector<event::Interaction> &truth, std::vector<event::RecoInteraction>& reco);

  /**
 * Enum to hold each different typoe of reconstructed event
 */
   enum InteractionMode {
    mCC = 0, 
    mNC = 1, 
    mCosmic = 2, 
    mOther = 3,
    mAll = 4
  };

  enum TrackMode {
    tmOther = -1,
    tmCosmic = 1,
    tmNeutrino = 2
  };


  struct CRTMatch {
    sbnd::crt::CRTTrack track;
    bool has_track_match;
    sbnd::crt::CRTHit hit;
    bool has_hit_match;
    double hit_distance;
    double match_time;
  };

  struct FlashMatch {
    double match_time;
    double match_time_first;
    double match_time_width;
  };

  struct TrackTruthMatch {
    bool has_match;
    bool mctruth_has_neutrino;
    TVector3 mctruth_vertex;
    int mctruth_origin;
    int mctruth_ccnc;
    int mcparticle_id;
    double completion;
    int match_pdg;
    TrackTruthMatch():
      has_match(false),
      mctruth_has_neutrino(false),
      mctruth_vertex(-1, -1, -1),
      mctruth_origin(-1),
      mctruth_ccnc(-1),
      mcparticle_id(-1),
      completion(-1),
      match_pdg(-1) {}
  };

  struct TruthMatch {
    bool has_match;
    InteractionMode mode; //!< mode of the interaction
    TrackMode tmode;
    int mctruth_vertex_id; //!< index of the truth vertex into the list of MCThruths. -1 if no match
    int event_vertex_id; //!< index of the truth vertex into the list of truth vertices generated by this class. -1 if no match
    int mctruth_track_id; //!< index of the primary track into the list of MCTruths. -1 if no match.
    int event_track_id; //!< index of the primary track into the list of truth vertices generated by this class. -1 if no match.
    double truth_vertex_distance;
    bool is_misreconstructed;
  };

  /** Reconstructed information about each particle. Internal struct used
 * to combine information on each reconstructed particle. 
 * */
  struct RecoParticle {
    bool p_is_clear_cosmic; //!< Taken from Pandora metadata "is_clear_cosmic"
    bool p_is_neutrino; //!< Taken from Pandora metadata "is_neutrino"
    double p_nu_score; //!< Take from Pandora metadata "nu_score"
    std::vector<geo::Point_t> vertices; //!< List of vertices associated with the particle
    std::vector<size_t> daughters; //!< Daughters of the particle in the "particle flow". Value represents index into pandora information.
    size_t self; //!< Index into pandora information of this particle
  };

  struct RecoTrack {
    // track specific info
    double deposited_energy_max;
    double deposited_energy_avg;
    double deposited_energy_med;
    double range_momentum;
    double range_momentum_muon;

    double fwd_mcs_momentum;
    double fwd_mcs_momentum_muon;
    double fwd_mcs_momentum_err;
    double fwd_mcs_momentum_muon_err;
    double bwd_mcs_momentum;
    double bwd_mcs_momentum_muon;
    double bwd_mcs_momentum_err;
    double bwd_mcs_momentum_muon_err;
    bool mcs_is_backward;

    // buest guess at momentum 
    double momentum;
    double energy;

    double chi2_proton;
    double chi2_kaon;
    double chi2_pion;
    double chi2_muon;
    double min_chi2;
    int pid_n_dof;
    int pdgid; //!< particle id

    bool is_muon;
    double length;
    double costh; //!< cosine of angle to z axis
    bool contained_in_cryo; //!< is it contained a single cryostat?
    bool contained_in_tpc; //!< is it contained in a single TPC?
    bool crosses_tpc; //!< does it cross a tpc?
    bool is_contained; //!< is it contained in the "containment volume"?
    TVector3 start; //!< start position of track
    TVector3 end; //!< end position of track
    double dist_to_vertex;
    TrackTruthMatch match;

    std::vector<CRTMatch> crt_match; 
    std::vector<FlashMatch> flash_match;
    int pandora_track_id;

    double stopping_chisq_start;
    double stopping_chisq_finish;
    std::vector<double> tpc_t0s;

    RecoTrack():
      deposited_energy_max(-1),
      deposited_energy_avg(-1),
      deposited_energy_med(-1),
      range_momentum(-1),
      range_momentum_muon(-1),
      fwd_mcs_momentum(-1),
      fwd_mcs_momentum_muon(-1),
      fwd_mcs_momentum_err(-1),
      fwd_mcs_momentum_muon_err(-1),
      bwd_mcs_momentum(-1),
      bwd_mcs_momentum_muon(-1),
      bwd_mcs_momentum_err(-1),
      bwd_mcs_momentum_muon_err(-1),
      mcs_is_backward(false),
      momentum(-1),
      energy(-1),
      chi2_proton(-1),
      chi2_kaon(-1),
      chi2_pion(-1),
      chi2_muon(-1),
      min_chi2(-1.5),
      pid_n_dof(-1),
      pdgid(-1),
      is_muon(-1),
      length(-1),
      costh(-999),
      contained_in_cryo(false),
      contained_in_tpc(false),
      crosses_tpc(false),
      is_contained(false),
      start(-999, -999, -999),
      end(-999, -999, -999),
      dist_to_vertex(-1),
      crt_match({}),
      flash_match({}),
      pandora_track_id(-1),
      stopping_chisq_start(-1),
      stopping_chisq_finish(-1),
      tpc_t0s()
      {}

    // More involved info -- need this later???
    // std::vector<TLorentzVector> trajectory;
    // std::vector<double> calo_dEdx;
    // std::vector<double> calo_extent;
  };

  struct RecoSlice {
    int primary_index;
    int primary_track_index;
    std::map<size_t, RecoParticle> particles;
    std::map<size_t, RecoTrack> tracks;
  };


  /**
 *  Reconstruction information for each neutrino vertex.
 *  Produced from both reconstruction and truth information
 */
  struct RecoInteraction {
    RecoSlice slice; //!< Particle content of the interaction
    TVector3 position; //!< location of the vertex
    double nu_energy; //!< true/reconstructed neutrino energy
    TruthMatch match; //!< Info for mathing to truth
    int multiplicity;
    RecoTrack primary_track;
  };


  /** Reconstruction Information about Event */
  struct RecoEvent {
    std::vector<RecoTrack> tracks;
    std::map<size_t, RecoTrack> true_tracks;
    std::vector<RecoInteraction> reco; //!< List of reconstructed vertices
    std::vector<RecoInteraction> truth; //!< List of truth vertices
  };


protected:
  /** Configuration parameters */
  struct Config {
    std::vector<geo::BoxBoundedGeo> fiducial_volumes; //!< List of FV containers -- set by "fiducial_volumes"
    std::vector<geo::BoxBoundedGeo> containment_volumes; //!< List of volumes for containment cuts -- set by "containment_volumes"
    std::vector<geo::BoxBoundedGeo> cryostat_volumes; //!< List of cryostat volumes -- retreived from Geometry service
    std::vector<std::vector<geo::BoxBoundedGeo>> tpc_volumes; //!< List of active tpc volumes -- retreived from Geoemtry service
    bool verbose; //!< Whether to print out info associated w/ selection.
    bool shakyMCTracks; //!< How to handle MC tracks with some missing truth information
    std::vector<std::string> uniformWeights; //!< Weights taken from "EventWeight" that should be applied to the weight of each event
    double constantWeight; //!< Constant weight to apply uniformly to each event
    double cosmicWeight; //!< Weight applied to all events matched to a cosmic track

    bool requireMatched; //!< Apply cut that requires each reconstructed vertex to be matched to a truth vertex
    bool requireTrack; //!< Apply cut that requires each reconstructed vertex to have an associated primary track
    bool requireContained; //!< Apply cut that requires each primary track to be contained inside the containment volume
    double trackMatchContainmentCut;

    bool CRTHitinOpHitRange;
    double CRT2OPTimeWidth;

    bool MakeOpHits;
    double CRTHitDist;

    int FlashMatchMethod;
    int TSMode;
    double flashMatchTimeDifference;

    double beamCenterX;
    double beamCenterY;

    std::string HitTag; //!< art tag for hits
    std::string RecoSliceTag;
    std::string RecoTrackTag; //!< art tag for reconstructed tracks
    std::string RecoVertexTag; //!< art tag for reconstructed vertices
    std::string CaloTag;
    std::string PIDTag;
    std::string PFParticleTag; //!< art tag for PFParticles
    std::string CorsikaTag; //!< art tag for corsika MCTruth
    std::string CRTTrackTag; //!< art tag for CRT tracks
    std::string CRTHitTag;
    std::string OpFlashTag;
    std::string MCParticleTag; //!< art tag for MCParticle 

  };


  // Internal functions

  /**
 * Produce all reconstruction information from the gallery event
 * \param ev the gallery Event
 * \param truth the list of truth vertices for this event
 * \return the RecoEvent object for this event
 */
  RecoEvent Reconstruct(const gallery::Event &ev, std::vector<RecoInteraction> truth);

  /**
 * Gathers together reconstruction information on each individual particle.
 * \param ev the gallery Event
 *
 * \return the list of RecoParticle objects for every reconstructed particle in the event
 */
  std::vector<RecoParticle> RecoParticleInfo(const gallery::Event &event);

  /**
 * Selects which RecoParticles are neutrino interaction candidates
 * \param reco_particles the list of all reconstructed particles to be considered
 *
 * \return the list of reconstructed particles which might be neutrinos
 */
  std::vector<RecoSlice> SelectSlices(const std::vector<RecoSlice> &reco_slices);
  std::vector<RecoTrack> RecoTrackInfo(const gallery::Event &event);

  std::vector<RecoSlice> RecoSliceInfo(
    const gallery::Event &event,
    const std::vector<RecoTrack> &reco_tracks,
    const std::vector<RecoParticle> &particles);

  int SelectPrimaryTrack(const RecoSlice &slice);

  std::map<size_t, RecoTrack> RecoSliceTracks(
    const gallery::Event &event, 
    const std::vector<RecoTrack> &reco_tracks, 
    const std::map<size_t, RecoParticle> &particles, 
    int primary_index);

  /**
 *  Converts the NumuRecoSelection::RecoInteraction information into reco information used by sbncode core
 *  \param truth the list of truth vertices produced by sbncode core
 *  \param vertex the reconstructed vertex produced by this selection
 *  \param weight the calculated weight for this interaction
 *
 *  \return Reconstruction information as needed by the sbncode core class
 */
  event::RecoInteraction CoreRecoInteraction(const std::vector<event::Interaction> &truth, const RecoInteraction &vertex, double weight);

  /**
 * Produced vertex information from truth information
 * \param ev the gallery Event
 *
 * \return the list of truth neutrino interactions for this event 
 */
  std::vector<RecoInteraction> MCTruthInteractions(const gallery::Event &ev, std::map<size_t, RecoTrack> &true_tracks);

  std::map<size_t, RecoTrack> MCParticleTracks(const gallery::Event &event);


  std::vector<FlashMatch> FlashMatching(const gallery::Event &ev, const recob::Track &pandora_track, const RecoTrack &track); 
  std::vector<CRTMatch> CRTMatching(const NumuRecoSelection::RecoTrack &track, const recob::Track &pandora_track, const std::vector<art::Ptr<recob::Hit>> &track_hits);

  /**
 * Get the primary track associated with a truth neutrino interaction.
 * \param ev the gallery Event
 * \param mctruth the MCTruth object for the considered truth neutrino interaction
 *
 * \return the index into the list of MCTrack's containing this track. Equal to -1 if no such track exists.
 */
  int MCTruthPrimaryTrack(const simb::MCTruth &mc_truth, const std::vector<simb::MCParticle> &mcparticle_list);

  /**
 * Get the primary track information associated with an mctruth object
 * \param ev the gallery Event
 * \param mc_truth the MCTruth object for the considered truth neutrino interaction
 *
 * \return information associated with the primary track. Set to nonsense if no such track exists.
 */
  std::map<size_t, RecoTrack> MCTruthTracks(
    std::map<size_t, RecoTrack> &true_tracks, 
    const art::FindManyP<simb::MCParticle, sim::GeneratedParticleInfo> &truth_to_particles, 
    const simb::MCTruth &mc_truth, 
    int mc_truth_index);

  int TrueTrackMultiplicity(const simb::MCTruth &mc_truth, const std::vector<simb::MCParticle> &mcparticle_list);

  /**
 * Get the TrackInfo information associated with an MCTrack
 * \param truth The neutrino interaction which produced this track
 * \param track The MCTrack information for this track
 *
 * \return reconstruction information associated with the truth track
 */
  RecoTrack MCTrackInfo(const simb::MCParticle &track);

  /** Helper function -- whether point is contained in fiducial volume list
 * \param v The point vector.
 *
 * \return Whether the point is contained in the configured list of fiducial volumes.
 * */
  bool containedInFV(const TVector3 &v);
  bool containedInFV(const geo::Point_t &v);

  /**
 * Calculate the associated topology of each primary track (i.e. whether the track is contained in things)
 * 
 * \param The reconstructed track information
 *
 * \return A list of bools associated with track topology. See the code for what is what.
 */
  std::array<bool, 4> RecoTrackTopology(const art::Ptr<recob::Track> &track);

  TrackTruthMatch MatchTrack2Truth(const gallery::Event &ev, size_t pfp_track_id);
  double TrackCompletion(int mcparticle_id, const std::vector<art::Ptr<recob::Hit>> &reco_track_hits);

  void CollectPMTInformation(const gallery::Event &ev);
  void CollectCRTInformation(const gallery::Event &ev);

  unsigned _event_counter;  //!< Count processed events
  unsigned _nu_count;  //!< Count selected events
  TGraph *_cut_counts; //!< Keep track of neutrinos per cut

  Config _config; //!< The config

  // calculators for Reco things
  trkf::TrackMomentumCalculator *_track_momentum_calculator;
  trkf::TrajectoryMCSFitter *_mcs_fitter;
  

  RecoEvent _recoEvent; //!< Branch container for the RecoEvent
  std::vector<RecoInteraction> *_selected; //!< Branch container for the list of selected reco vertices

  sbnd::CRTTrackMatchAlg *_crt_track_matchalg; //!< Algorithm for matching reco Tracks -> CRT Tracks
  sbnd::CRTT0MatchAlg *_crt_hit_matchalg; //!< Algorithm for matching reco Tracks -> CRT hits (T0's)
  ApaCrossCosmicIdAlg _apa_cross_cosmic_alg;
  StoppingParticleCosmicIdAlg _stopping_cosmic_alg;
  opdet::opHitFinderSBND *_op_hit_maker;

  // holders for CRT information
  const std::vector<sbnd::crt::CRTTrack> *_crt_tracks;
  std::vector<sbnd::crt::CRTTrack> _crt_tracks_local;
  std::vector<sbnd::crt::CRTHit> _crt_hits_local; 
  const std::vector<sbnd::crt::CRTHit> *_crt_hits; 
  bool _has_crt_hits;
  bool _has_crt_tracks;

  // holders for PMT information
  std::vector<art::Ptr<recob::OpHit>> _op_hit_ptrs;
  std::vector<recob::OpHit> _op_hits_local;
};

  }  // namespace SBNOsc
}  // namespace ana

#endif  // __sbnanalysis_ana_SBNOsc_NumuRecoSelection__

