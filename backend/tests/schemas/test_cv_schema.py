from src.models import CandidateDocument, CandidateProfile, CandidateScreening


def test_cv_models_are_exported() -> None:
    assert CandidateDocument.__tablename__ == "candidate_documents"
    assert CandidateProfile.__tablename__ == "candidate_profiles"
    assert CandidateScreening.__tablename__ == "candidate_screenings"
