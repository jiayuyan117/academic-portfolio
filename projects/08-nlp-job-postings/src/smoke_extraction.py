"""Keep sample-trained private models separate from full-research models."""
import skill_extraction


if __name__ == "__main__":
    skill_extraction.RUNTIME = skill_extraction.PROJECT / ".runtime/smoke/models"
    skill_extraction.main()
